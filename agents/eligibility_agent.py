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
        manual_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process an eligibility request, call MCP tools or EligibilitySkill directly.
        Returns structured JSON with Eligibility, Reason, Next eligible date, Explanation.
        """
        logger.info(f"Eligibility Agent processing request: {user_request}")
        
        try:
            skill_result = None
            mcp_result = None
            
            # 1. Evaluate using EligibilitySkill & MCP Tool if donor_id is provided
            if donor_id is not None:
                # Direct skill evaluation
                eligibility_res = self.eligibility_skill.evaluate_donor(donor_id)
                skill_result = {
                    "status": eligibility_res.status,
                    "reason": eligibility_res.reason,
                    "metadata": eligibility_res.metadata
                }
                
                # Fetch deeper context using MCP Tool
                try:
                    check_tool = registry.get_tool("check_donor_eligibility")
                    mcp_res = check_tool(donor_id=donor_id)
                    if mcp_res.get("status") == "success":
                        mcp_result = mcp_res.get("data")
                except Exception as mcp_err:
                    logger.error(f"Failed to call MCP check_donor_eligibility: {mcp_err}")
                    
            # 2. Evaluate using manual parameters if provided (for walk-in donors)
            elif manual_params:
                eligibility_res = self.eligibility_skill.evaluate_manual(**manual_params)
                skill_result = {
                    "status": eligibility_res.status,
                    "reason": eligibility_res.reason,
                    "metadata": eligibility_res.metadata
                }
                
            # 3. Use LLM to analyze the findings and structure the JSON response
            analysis_prompt = (
                f"User Request: '{user_request}'\n\n"
                f"Eligibility Skill Output: {json.dumps(skill_result) if skill_result else 'None'}\n\n"
                f"MCP Tool Output: {json.dumps(mcp_result) if mcp_result else 'None'}\n\n"
                "Task:\n"
                "Analyze the data and provide a clear eligibility determination.\n"
                "Estimate the 'Next eligible date' based on standard WHO wait periods if they are temporarily deferred, or return 'N/A' if permanently deferred or eligible today.\n"
                "IMPORTANT: Your output MUST be a valid JSON object matching the following structure exactly:\n"
                "{\n"
                '  "eligibility": "Eligible / Temporary Deferral / Permanent Deferral",\n'
                '  "reason": "Brief reason",\n'
                '  "next_eligible_date": "YYYY-MM-DD or N/A",\n'
                '  "explanation": "Detailed natural language explanation for the hospital staff"\n'
                "}\n"
                "Return ONLY the JSON string. Do not include markdown formatting like ```json."
            )
            
            response_text = ai_client.generate(
                prompt=analysis_prompt,
                agent_name="eligibility",
                system_instruction=self.prompt
            ).strip()
            
            # Clean up potential markdown formatting from LLM
            if response_text.startswith("```json"):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith("```"):
                response_text = response_text[3:-3].strip()
                
            final_json = json.loads(response_text)
            logger.info("Eligibility Agent completed task successfully.")
            return final_json
            
        except json.JSONDecodeError as e:
            logger.error(f"Eligibility Agent failed to parse LLM JSON: {e}\nResponse text: {response_text}")
            return {
                "eligibility": "Error",
                "reason": "Failed to generate structured JSON.",
                "next_eligible_date": "N/A",
                "explanation": str(e)
            }
        except Exception as e:
            logger.error(f"Eligibility Agent encountered an error: {e}", exc_info=True)
            return {
                "eligibility": "Error",
                "reason": "Internal agent error.",
                "next_eligible_date": "N/A",
                "explanation": str(e)
            }
