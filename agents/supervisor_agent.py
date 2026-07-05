"""
Supervisor Agent for BloodLink AI.
Orchestrates requests by delegating to specialized sub-agents using Google GenAI SDK.
"""

import os
import google.generativeai as genai
from typing import Dict, Any, List
from agents.prompts import SUPERVISOR_PROMPT
from utils.logger import logger

class SupervisorAgent:
    def __init__(self):
        """Initialize the Supervisor Agent and configure Google GenAI."""
        self.prompt = SUPERVISOR_PROMPT
        
        # Configure Google GenAI SDK
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
        else:
            logger.warning("GEMINI_API_KEY not found in environment variables.")
            
        # In a complete implementation, sub-agents would be instantiated here:
        # self.inventory_agent = InventoryAgent()
        # self.eligibility_agent = EligibilityAgent()
        # self.priority_agent = PriorityAgent()
        # self.recommendation_agent = RecommendationAgent()
        # self.notification_agent = NotificationAgent()

    def process_request(self, user_request: str) -> Dict[str, Any]:
        """
        Receive user request, understand intent, delegate work, and consolidate response.
        Does NOT directly query the database.
        """
        logger.info(f"Supervisor received request: {user_request}")
        
        try:
            # 1. Understand Intent and Delegate
            model = genai.GenerativeModel(
               model_name="gemini-3.5-flash",
                system_instruction=self.prompt
            )
            
            routing_prompt = (
                f"User Request: {user_request}\n\n"
                "Analyze the request and determine which of the following agents must be called: "
                "Inventory, Eligibility, Priority, Recommendation, Notification.\n"
                "Return a comma-separated list of the required agent names. Do not include any other text."
            )
            
            routing_response = model.generate_content(routing_prompt)
            agents_to_call = [a.strip().lower() for a in routing_response.text.split(',')]
            
            reasoning = (
                f"Analyzed the request: '{user_request}'. "
                f"Determined intent requires delegation to the following agents: {', '.join(agents_to_call)}."
            )
            logger.info(reasoning)
            
            # 2. Execute Work via Sub-Agents
            # (Mocked execution for this template. Real implementation would call agent.execute())
            delegated_responses = {}
            for agent in agents_to_call:
                if agent:
                    delegated_responses[agent] = f"Simulated success response from {agent} agent."
                
            # 3. Consolidate Final Response and Explain Reasoning
            consolidation_prompt = (
                f"User Request: '{user_request}'\n"
                f"Delegated Agent Responses: {delegated_responses}\n\n"
                "Task:\n"
                "1. Provide a consolidated final response addressing the user's request.\n"
                "2. Clearly explain your reasoning and the workflow used to arrive at this answer.\n"
                "Ensure the tone is professional and suitable for hospital staff."
            )
            
            final_result = model.generate_content(consolidation_prompt)
            
            return {
                "status": "Success",
                "workflow_reasoning": reasoning,
                "delegated_data": delegated_responses,
                "final_answer": final_result.text
            }
            
        except Exception as e:
            logger.error(f"Supervisor encountered an error: {e}", exc_info=True)
            return {
                "status": "Error",
                "workflow_reasoning": "Failed to process request due to internal error.",
                "final_answer": str(e)
            }
