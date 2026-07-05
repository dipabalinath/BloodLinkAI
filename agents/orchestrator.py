"""
Orchestrator for BloodLink AI.
Manages the end-to-end workflow from User Request to Final Answer.
"""

import os
import json
from utils import ai_client
from typing import Dict, Any, List
from agents.agent_factory import get_agents
from utils.logger import logger

class BloodLinkOrchestrator:
    def __init__(self):
        """Initialize the Orchestrator and load all specialized agents."""
        logger.info("Initializing BloodLink Orchestrator...")
        self.agents = get_agents()
        self.supervisor = self.agents.get("supervisor")
    def process_request(self, user_request: str, context_params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        End-to-end workflow:
        User Request -> Supervisor -> Delegate -> Specialized Agents -> MCP Server/Skills -> Merge -> Final Answer
        """
        logger.info(f"Orchestrator received new request: {user_request}")
        if context_params is None:
            context_params = {}
            
        try:
            # 1. Supervisor Agent Routing
            logger.info("Step 1: Passing request to Supervisor for delegation routing.")
            
            routing_prompt = (
                f"User Request: '{user_request}'\n\n"
                "Analyze the request and determine which of the following agents must be called: "
                "Inventory, Eligibility, Priority, Recommendation, Notification.\n"
                "Return a comma-separated list of the required agent names. Do not include any other text."
            )
            
            routing_res_text = ai_client.generate(
                prompt=routing_prompt,
                agent_name="supervisor",
                system_instruction=self.supervisor.prompt
            )
            
            if isinstance(routing_res_text, dict):
                agents_to_call = routing_res_text.get("delegated_agents", [])
            else:
                try:
                    parsed = json.loads(routing_res_text)
                    agents_to_call = parsed.get("delegated_agents", [])
                except (json.JSONDecodeError, TypeError, AttributeError):
                    agents_to_call = [a.strip().lower() for a in routing_res_text.split(',')]
                    
            logger.info(f"Supervisor delegated to: {agents_to_call}")
            
            # 2. Delegate to Specialized Agents
            logger.info("Step 2: Executing Specialized Agents (which call MCP Servers and Skills).")
            agent_responses = {}
            
            for agent_name in agents_to_call:
                if not agent_name: continue
                
                agent = self.agents.get(agent_name)
                if not agent:
                    logger.warning(f"Requested agent '{agent_name}' not found in Agent Factory.")
                    continue
                    
                logger.info(f"Executing {agent_name.capitalize()} Agent...")
                
                # Execute based on agent type and available context params
                try:
                    if agent_name == "inventory":
                        resp = agent.execute(
                            user_request=user_request,
                            blood_group=context_params.get("blood_group"),
                            component_type=context_params.get("component_type", "Packed RBC"),
                            latitude=context_params.get("latitude"),
                            longitude=context_params.get("longitude"),
                            required_units=context_params.get("required_units", 1)
                        )
                    elif agent_name == "eligibility":
                        resp = agent.execute(
                            user_request=user_request,
                            donor_id=context_params.get("donor_id"),
                            manual_params=context_params.get("manual_params")
                        )
                    elif agent_name == "priority":
                        resp = agent.execute(
                            user_request=user_request,
                            request_id=context_params.get("request_id"),
                            patient_condition=context_params.get("patient_condition", ""),
                            hemodynamic_status=context_params.get("hemodynamic_status", "")
                        )
                    elif agent_name == "recommendation":
                        resp = agent.execute(
                            user_request=user_request,
                            blood_group=context_params.get("blood_group", "O-"), 
                            component_type=context_params.get("component_type", "Packed RBC"),
                            latitude=context_params.get("latitude", 0.0),
                            longitude=context_params.get("longitude", 0.0),
                            required_units=context_params.get("required_units", 1)
                        )
                    elif agent_name == "notification":
                        resp = agent.execute(
                            user_request=user_request,
                            blood_group=context_params.get("blood_group", "O-"),
                            urgency=context_params.get("urgency", "high"),
                            location=context_params.get("location", "Central Hospital"),
                            inventory_available=context_params.get("inventory_available", False)
                        )
                    else:
                        resp = {"status": "Unknown Agent", "data": None}
                        
                    agent_responses[agent_name] = resp
                    logger.info(f"{agent_name.capitalize()} Agent execution complete.")
                    
                except Exception as ex:
                    logger.error(f"Error executing {agent_name} agent: {ex}")
                    agent_responses[agent_name] = {"error": str(ex)}

            # 3. Merge Responses
            logger.info("Step 3: Supervisor merging responses into final answer.")
            consolidation_prompt = (
                f"User Request: '{user_request}'\n"
                f"Delegated Agent Responses: {json.dumps(agent_responses)}\n\n"
                "Task:\n"
                "1. Provide a consolidated, natural-language final response addressing the user's request.\n"
                "2. Synthesize the findings from all agents.\n"
                "3. Explain the reasoning behind the final answer in a clear, staff-friendly format.\n"
            )
            
            final_result_text = ai_client.generate(
                prompt=consolidation_prompt,
                agent_name="supervisor",
                system_instruction=self.supervisor.prompt
            )
            
            if isinstance(final_result_text, dict):
                final_answer = final_result_text.get("final_answer", str(final_result_text))
            else:
                try:
                    parsed = json.loads(final_result_text)
                    final_answer = parsed.get("final_answer", final_result_text)
                except (json.JSONDecodeError, TypeError, AttributeError):
                    final_answer = final_result_text
            
            logger.info("Orchestrator workflow complete.")
            return {
                "status": "Success",
                "user_request": user_request,
                "agents_involved": agents_to_call,
                "agent_data": agent_responses,
                "final_answer": final_answer
            }
            
        except Exception as e:
            logger.error(f"Orchestrator encountered a critical error: {e}", exc_info=True)
            return {
                "status": "Error",
                "user_request": user_request,
                "error": str(e),
                "final_answer": "System encountered an error while orchestrating the request."
            }
