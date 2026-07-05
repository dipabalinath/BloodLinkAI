"""
Priority Agent for BloodLink AI.
Determines blood request priority using Google GenAI SDK and PrioritySkill.
"""

import os
import json
from utils import ai_client
from typing import Dict, Any, Optional
from agents.prompts import PRIORITY_AGENT_PROMPT
from skills.priority_skill import PrioritySkill
from utils.logger import logger

class PriorityAgent:
    def __init__(self):
        """Initialize the Priority Agent with Google GenAI and PrioritySkill."""
        self.prompt = PRIORITY_AGENT_PROMPT
        self.priority_skill = PrioritySkill()

    def execute(
        self, 
        user_request: str, 
        request_id: Optional[int] = None,
        patient_condition: str = "",
        hemodynamic_status: str = ""
    ) -> Dict[str, Any]:
        """
        Process a priority evaluation request via PrioritySkill and LLM analysis.
        Returns structured JSON with Priority, Reason, and WHO explanation.
        """
        logger.info(f"Priority Agent processing request: {user_request}")
        
        try:
            skill_result = None
            
            # 1. Evaluate using PrioritySkill
            if request_id is not None:
                priority_res = self.priority_skill.evaluate_request(request_id)
            else:
                priority_res = self.priority_skill.evaluate_condition(
                    patient_condition, hemodynamic_status
                )
                
            skill_result = {
                "status": priority_res.status,
                "reason": priority_res.reason,
                "metadata": priority_res.metadata
            }
                
            # 2. Use LLM to analyze the findings and structure the JSON response
            analysis_prompt = (
                f"User Request: '{user_request}'\n\n"
                f"Priority Skill Output: {json.dumps(skill_result)}\n\n"
                "Task:\n"
                "Analyze the data and provide a clear priority determination based on the provided WHO guidelines:\n"
                "- Tier 1: Birthing Mother, Active hemorrhage, Shock\n"
                "- Tier 2: Critical Thalassemia, Heart failure, Hemodynamic instability\n"
                "- Tier 3: Routine Thalassemia, Scheduled transfusion\n"
                "- Tier 4: Elective Surgery\n\n"
                "IMPORTANT: Your output MUST be a valid JSON object matching the following structure exactly:\n"
                "{\n"
                '  "priority": "TIER_1_IMMEDIATE / TIER_2_URGENT / TIER_3_SCHEDULED / TIER_4_ELECTIVE",\n'
                '  "reason": "Clinical reason for the decision",\n'
                '  "who_explanation": "Detailed explanation based on WHO rules"\n'
                "}\n"
                "Return ONLY the JSON string. Do not include markdown formatting like ```json."
            )
            
            response_text = ai_client.generate(
                prompt=analysis_prompt,
                agent_name="priority",
                system_instruction=self.prompt
            ).strip()
            
            # Clean up potential markdown formatting from LLM
            if response_text.startswith("```json"):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith("```"):
                response_text = response_text[3:-3].strip()
                
            final_json = json.loads(response_text)
            logger.info("Priority Agent completed task successfully.")
            return final_json
            
        except json.JSONDecodeError as e:
            logger.error(f"Priority Agent failed to parse LLM JSON: {e}\nResponse text: {response_text}")
            return {
                "priority": "Error",
                "reason": "Failed to generate structured JSON.",
                "who_explanation": str(e)
            }
        except Exception as e:
            logger.error(f"Priority Agent encountered an error: {e}", exc_info=True)
            return {
                "priority": "Error",
                "reason": "Internal agent error.",
                "who_explanation": str(e)
            }
