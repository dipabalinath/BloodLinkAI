"""
Eligibility Agent for BloodLink AI.
Evaluates donor eligibility using Google GenAI SDK, MCP donor tools, and EligibilitySkill.
"""

import os
import json
from utils import ai_client
from typing import Dict, Any, Optional
from agents.prompts import ELIGIBILITY_AGENT_PROMPT
from skills.eligibility_skill import EligibilitySkill
from mcp_server.registry import registry
from utils.logger import logger

class EligibilityAgent:
    def __init__(self):
        """Initialize the Eligibility Agent with Google GenAI and skills."""
        self.prompt = ELIGIBILITY_AGENT_PROMPT
        self.eligibility_skill = EligibilitySkill()

    def execute(
        self, 
        user_request: str, 
        donor_id: Optional[int] = None,
        manual_params: Optional[Dict[str, Any]] = None,
        context_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process an eligibility request using deterministic rules and LLM synthesis.
        """
        logger.info(f"Eligibility Agent processing request: {user_request}")
        
        try:
            # 1. Deterministic Screening Rules
            is_eligible_deterministic = True
            reasons = []
            risk_indicators = {
                "Age": "✅",
                "Weight": "✅",
                "Haemoglobin": "✅",
                "Blood Pressure": "✅",
                "Last Donation Interval": "✅",
                "Medical History": "✅",
                "Symptoms": "✅"
            }
            
            if manual_params:
                # Age
                if manual_params.get("Age", 0) < 18:
                    is_eligible_deterministic = False
                    reasons.append("Donor is under 18 years of age.")
                    risk_indicators["Age"] = "❌"
                    
                # Weight
                if manual_params.get("Weight", 0) < 45.0:
                    is_eligible_deterministic = False
                    reasons.append("Weight is below the minimum threshold of 45 kg.")
                    risk_indicators["Weight"] = "❌"
                    
                # Haemoglobin
                hb = manual_params.get("Haemoglobin", 0)
                if hb < 12.5:
                    is_eligible_deterministic = False
                    reasons.append("Haemoglobin is below the minimum threshold (12.5 g/dL).")
                    risk_indicators["Haemoglobin"] = "❌"
                    
                # Blood Pressure (rough check)
                sys = manual_params.get("Systolic", 120)
                dia = manual_params.get("Diastolic", 80)
                if sys > 180 or sys < 90 or dia > 100 or dia < 50:
                    is_eligible_deterministic = False
                    reasons.append("Blood pressure is outside acceptable limits.")
                    risk_indicators["Blood Pressure"] = "❌"
                    
                # Donation Interval (approx 90 days)
                from datetime import datetime
                last_donation = manual_params.get("Last Donation Date")
                if last_donation:
                    try:
                        ld_date = datetime.strptime(str(last_donation), "%Y-%m-%d")
                        if (datetime.now() - ld_date).days < 90:
                            is_eligible_deterministic = False
                            reasons.append("Donation date is within the last 3 months.")
                            risk_indicators["Last Donation Interval"] = "❌"
                    except:
                        pass
                        
                # Medical History
                medical_flags = []
                if manual_params.get("Pregnant/Breastfeeding"): medical_flags.append("Pregnant or Breastfeeding")
                if manual_params.get("Recent Surgery"): medical_flags.append("Recent Surgery")
                if manual_params.get("Any Infectious Disease"): medical_flags.append("Infectious Disease")
                if manual_params.get("Chronic Disease"): medical_flags.append("Chronic Disease")
                if manual_params.get("Travel History"): medical_flags.append("Travel History")
                if manual_params.get("Recent Vaccination"): medical_flags.append("Recent Vaccination")
                if manual_params.get("Alcohol Consumption"): medical_flags.append("Alcohol Consumption")
                if manual_params.get("Recent Tattoo/Piercing (<6 months)"): medical_flags.append("Recent Tattoo/Piercing")
                
                if medical_flags:
                    is_eligible_deterministic = False
                    reasons.extend(medical_flags)
                    risk_indicators["Medical History"] = "❌"
                    
                # Symptoms
                symptoms = manual_params.get("Symptoms", [])
                if symptoms and "None" not in symptoms:
                    is_eligible_deterministic = False
                    reasons.append(f"Active symptoms reported: {', '.join(symptoms)}")
                    risk_indicators["Symptoms"] = "❌"
                    
            # Set deterministic status
            status_text = "Eligible" if is_eligible_deterministic else "Deferred"
            if not is_eligible_deterministic and any(w in str(reasons).lower() for w in ["cancer", "infectious disease"]):
                status_text = "Ineligible"
                
            # 2. Use LLM to generate clinical summary and recommendations
            analysis_prompt = (
                f"User Request: '{user_request}'\n\n"
                f"Donor Data: {json.dumps(manual_params)}\n\n"
                f"Deterministic Assessment: {status_text}. Reasons: {reasons}\n\n"
                "Task:\n"
                "Generate a professional clinical summary and recommendations based on the donor's profile and deterministic assessment.\n"
                "IMPORTANT: Your output MUST be a valid JSON object matching the following structure exactly:\n"
                "{\n"
                '  "status": "Success",\n'
                f'  "eligibility": "{status_text}",\n'
                '  "reason": "Explain WHY the donor is eligible or deferred, mentioning every important parameter."\n'
                "}\n"
                "Return ONLY the JSON string. Do not include markdown formatting like ```json."
            )
            
            response_text = ai_client.generate(
                prompt=analysis_prompt,
                agent_name="eligibility",
                system_instruction=self.prompt,
                context_params=context_params
            ).strip()
            
            # Clean up potential markdown formatting from LLM
            if response_text.startswith("```json"):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith("```"):
                response_text = response_text[3:-3].strip()
                
            final_json = json.loads(response_text)
            
            # Merge deterministic risk indicators
            final_json["risk_indicators"] = risk_indicators
            
            # Force the correct eligibility status (prevent LLM hallucinations)
            final_json["eligibility"] = status_text
            
            logger.info("Eligibility Agent completed task successfully.")
            return final_json
            
        except json.JSONDecodeError as e:
            logger.error(f"Eligibility Agent failed to parse LLM JSON: {e}\nResponse text: {response_text}")
            return {
                "status": "Error",
                "eligibility": "Error",
                "reason": str(e)
            }
        except Exception as e:
            logger.error(f"Eligibility Agent encountered an error: {e}", exc_info=True)
            return {
                "status": "Error",
                "eligibility": "Error",
                "reason": str(e)
            }
