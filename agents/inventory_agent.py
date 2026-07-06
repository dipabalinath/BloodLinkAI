"""
Inventory Agent for BloodLink AI.
Manages inventory queries, facility recommendations, and compatibility matching using Google GenAI SDK.
"""

import os
import json
from utils import ai_client
from typing import Dict, Any, Optional
from agents.prompts import INVENTORY_AGENT_PROMPT
from skills.recommendation_skill import RecommendationSkill
from mcp_server.registry import registry
from utils.logger import logger

class InventoryAgent:
    def __init__(self):
        """Initialize the Inventory Agent with Google GenAI and skills."""
        self.prompt = INVENTORY_AGENT_PROMPT
        self.recommendation_skill = RecommendationSkill()

    def execute(
        self, 
        user_request: str, 
        blood_group: Optional[str] = None, 
        component_type: Optional[str] = "Packed RBC",
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        required_units: int = 1,
        context_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process an inventory-related request, call MCP tools, and use RecommendationSkill.
        Returns a structured JSON dict.
        """
        logger.info(f"Inventory Agent processing request: {user_request}")
        
        try:
            # 1. Use MCP tool for raw inventory search if blood group is provided
            raw_inventory = []
            if blood_group:
                find_inventory_tool = registry.get_tool("find_inventory")
                res = find_inventory_tool(
                    blood_group=blood_group, 
                    component_type=component_type, 
                    minimum_units=required_units,
                    allow_substitutes=True
                )
                if res.get("status") == "success":
                    raw_inventory = res.get("data", [])
                    
            # 2. Use RecommendationSkill for ranked nearby facilities if location is provided
            recommendation_data = None
            if blood_group and latitude is not None and longitude is not None:
                rec_result = self.recommendation_skill.recommend_inventory(
                    blood_group=blood_group,
                    component_type=component_type,
                    latitude=latitude,
                    longitude=longitude,
                    required_units=required_units
                )
                recommendation_data = {
                    "status": rec_result.status,
                    "reason": rec_result.reason,
                    "options": rec_result.metadata.get("options", [])
                }

            if context_params is None:
                context_params = {}
                
            context_params["raw_inventory"] = raw_inventory
            if recommendation_data:
                context_params["recommendation_data"] = recommendation_data

            # 3. Use LLM to analyze the findings and structure the JSON response
            analysis_prompt = (
                f"User Request: '{user_request}'\n\n"
                f"Raw Inventory Data (from MCP tool): {json.dumps(raw_inventory)}\n\n"
                f"Recommendation Skill Output: {json.dumps(recommendation_data) if recommendation_data else 'None provided.'}\n\n"
                "Task:\n"
                "Analyze the data and provide a response addressing the user's request.\n"
                "Explain your reasoning for any recommendations, highlighting compatible blood groups if exact matches were unavailable.\n"
                "IMPORTANT: Your output MUST be a valid JSON object matching the following structure exactly:\n"
                "{\n"
                '  "status": "Success",\n'
                '  "summary": "High level summary of findings",\n'
                '  "explanation": "Detailed explanation of recommendations and compatibility",\n'
                '  "recommended_facilities": [\n'
                '    {\n'
                '      "facility_id": 1,\n'
                '      "facility_name": "Name",\n'
                '      "facility_address": "Address",\n'
                '      "distance_km": 0.0,\n'
                '      "available_units": 0,\n'
                '      "blood_group": "A+",\n'
                '      "component_type": "Packed RBC"\n'
                '    }\n'
                '  ]\n'
                "}\n"
                "Return ONLY the JSON string. Do not include markdown formatting like ```json."
            )
            
            response_text = ai_client.generate(
                prompt=analysis_prompt,
                agent_name="inventory",
                system_instruction=self.prompt,
                context_params=context_params
            ).strip()
            
            # Clean up potential markdown formatting from LLM
            if response_text.startswith("```json"):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith("```"):
                response_text = response_text[3:-3].strip()
                
            final_json = json.loads(response_text)
            logger.info("Inventory Agent completed task successfully.")
            return final_json
            
        except json.JSONDecodeError as e:
            logger.error(f"Inventory Agent failed to parse LLM JSON: {e}\nResponse text: {response_text}")
            return {
                "status": "Error",
                "summary": "Failed to generate structured JSON.",
                "explanation": str(e),
                "recommended_facilities": []
            }
        except Exception as e:
            logger.error(f"Inventory Agent encountered an error: {e}", exc_info=True)
            return {
                "status": "Error",
                "summary": "Internal agent error.",
                "explanation": str(e),
                "recommended_facilities": []
            }
