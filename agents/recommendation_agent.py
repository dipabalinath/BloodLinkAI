"""
Recommendation Agent for BloodLink AI.
Determines the best hospital and inventory options using Google GenAI SDK and RecommendationSkill.
"""

import os
import json
from utils import ai_client
from typing import Dict, Any, Optional
from agents.prompts import RECOMMENDATION_AGENT_PROMPT
from skills.recommendation_skill import RecommendationSkill
from utils.logger import logger

class RecommendationAgent:
    def __init__(self):
        """Initialize the Recommendation Agent with Google GenAI and RecommendationSkill."""
        self.prompt = RECOMMENDATION_AGENT_PROMPT
        self.recommendation_skill = RecommendationSkill()

    def execute(
        self, 
        user_request: str, 
        blood_group: str,
        component_type: str,
        latitude: float,
        longitude: float,
        required_units: int,
        context_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a recommendation request via RecommendationSkill and LLM analysis.
        Returns structured JSON with Top Recommendation, Alternatives, and Reasoning.
        """
        logger.info(f"Recommendation Agent processing request: {user_request}")
        
        try:
            # 1. Evaluate using RecommendationSkill
            rec_result = self.recommendation_skill.recommend_inventory(
                blood_group=blood_group,
                component_type=component_type,
                latitude=latitude,
                longitude=longitude,
                required_units=required_units
            )
            
            skill_result = {
                "status": rec_result.status,
                "reason": rec_result.reason,
                "options": rec_result.metadata.get("options", [])
            }
                
            # 2. Use LLM to analyze the findings and structure the JSON response
            analysis_prompt = (
                f"User Request: '{user_request}'\n\n"
                f"Recommendation Skill Output: {json.dumps(skill_result)}\n\n"
                "Task:\n"
                "Analyze the ranked inventory options provided by the skill.\n"
                "Extract the top recommendation and up to 3 alternatives.\n"
                "Explain the reasoning based on Distance, Inventory availability, Expiry dates, and Compatibility.\n"
                "IMPORTANT: Your output MUST be a valid JSON object matching the following structure exactly:\n"
                "{\n"
                '  "status": "Success",\n'
                '  "recommendation": "Detailed explanation of why the top recommendation was chosen over alternatives"\n'
                "}\n"
                "If no options exist, set top_recommendation and alternatives to null/empty and explain why.\n"
                "Return ONLY the JSON string. Do not include markdown formatting like ```json."
            )
            
            response_text = ai_client.generate(
                prompt=analysis_prompt,
                agent_name="recommendation",
                system_instruction=self.prompt,
                context_params=context_params
            ).strip()
            
            # Clean up potential markdown formatting from LLM
            if response_text.startswith("```json"):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith("```"):
                response_text = response_text[3:-3].strip()
                
            final_json = json.loads(response_text)
            logger.info("Recommendation Agent completed task successfully.")
            return final_json
            
        except json.JSONDecodeError as e:
            logger.error(f"Recommendation Agent failed to parse LLM JSON: {e}\nResponse text: {response_text}")
            return {
                "status": "Error",
                "recommendation": "Failed to generate structured JSON."
            }
        except Exception as e:
            logger.error(f"Recommendation Agent encountered an error: {e}", exc_info=True)
            return {
                "status": "Error",
                "recommendation": f"Internal agent error: {str(e)}"
            }
