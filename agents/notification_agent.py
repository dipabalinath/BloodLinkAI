"""
Notification Agent for BloodLink AI.
Manages donor outreach using Google GenAI SDK and NotificationSkill.
"""

import os
import json
from utils import ai_client
from typing import Dict, Any
from agents.prompts import NOTIFICATION_AGENT_PROMPT
from skills.notification_skill import NotificationSkill
from mcp_server.registry import registry
from utils.logger import logger

class NotificationAgent:
    def __init__(self):
        """Initialize the Notification Agent with Google GenAI and NotificationSkill."""
        self.prompt = NOTIFICATION_AGENT_PROMPT
        self.notification_skill = NotificationSkill()

    def execute(
        self, 
        user_request: str, 
        blood_group: str,
        urgency: str,
        location: str,
        inventory_available: bool = False
    ) -> Dict[str, Any]:
        """
        Process a notification request via NotificationSkill and LLM analysis.
        If inventory is unavailable, prioritizes eligible donors (last donation > 90 days).
        Returns structured JSON summary of notifications.
        """
        logger.info(f"Notification Agent processing request: {user_request}")
        
        try:
            skill_result = None
            log_results = []
            
            # If inventory is unavailable, search and notify donors
            if not inventory_available:
                # 1. Evaluate using NotificationSkill
                notif_res = self.notification_skill.prepare_notification(
                    blood_group=blood_group,
                    urgency=urgency,
                    location=location,
                    limit=20 # Arbitrary limit for emergency dispatch
                )
                
                skill_result = {
                    "status": notif_res.status,
                    "reason": notif_res.reason,
                    "metadata": notif_res.metadata
                }
                
                # 2. Log notifications using MCP notification_tools
                if notif_res.status == "Success":
                    try:
                        record_tool = registry.get_tool("record_notification")
                        for msg in notif_res.metadata.get("messages", []):
                            # Record SMS/Email dispatched
                            res = record_tool(
                                donor_id=msg.get("donor_id"),
                                message_type="SMS/Email",
                                status="Sent"
                            )
                            if res.get("status") == "success":
                                log_results.append(msg.get("donor_id"))
                    except Exception as mcp_err:
                        logger.error(f"Failed to log notifications via MCP tool: {mcp_err}")
                
            # 3. Use LLM to analyze the findings and structure the JSON response
            analysis_prompt = (
                f"User Request: '{user_request}'\n\n"
                f"Inventory Available: {inventory_available}\n"
                f"Notification Skill Output: {json.dumps(skill_result) if skill_result else 'None'}\n\n"
                f"Successfully Logged Donor IDs: {log_results}\n\n"
                "Task:\n"
                "Analyze the notification dispatch process.\n"
                "If inventory was unavailable, confirm how many donors were found who are eligible (last donation > 90 days).\n"
                "Extract a summary of the SMS and Email templates used.\n"
                "IMPORTANT: Your output MUST be a valid JSON object matching the following structure exactly:\n"
                "{\n"
                '  "status": "Success",\n'
                '  "donors_notified": 5,\n'
                '  "sample_sms": "The generated SMS text",\n'
                '  "sample_email": "The generated Email text",\n'
                '  "summary": "Detailed explanation of the outreach campaign"\n'
                "}\n"
                "Return ONLY the JSON string. Do not include markdown formatting like ```json."
            )
            
            response_text = ai_client.generate(
                prompt=analysis_prompt,
                agent_name="notification",
                system_instruction=self.prompt
            ).strip()
            
            # Clean up potential markdown formatting from LLM
            if response_text.startswith("```json"):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith("```"):
                response_text = response_text[3:-3].strip()
                
            final_json = json.loads(response_text)
            logger.info("Notification Agent completed task successfully.")
            return final_json
            
        except json.JSONDecodeError as e:
            logger.error(f"Notification Agent failed to parse LLM JSON: {e}\nResponse text: {response_text}")
            return {
                "status": "Error",
                "donors_notified": 0,
                "sample_sms": "",
                "sample_email": "",
                "summary": "Failed to generate structured JSON."
            }
        except Exception as e:
            logger.error(f"Notification Agent encountered an error: {e}", exc_info=True)
            return {
                "status": "Error",
                "donors_notified": 0,
                "sample_sms": "",
                "sample_email": "",
                "summary": f"Internal agent error: {str(e)}"
            }
