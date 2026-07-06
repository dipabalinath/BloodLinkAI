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

from config.settings import settings

def build_final_answer(agent_responses: Dict[str, Any], user_request: str) -> dict:
    """Convert structured agent outputs into a structured Clinical Summary JSON and rich Markdown document."""
    if settings.USE_MOCK_AI:
        logger.info("MOCK_MODE is enabled. Building rich clinical synthesis manually.")
        
        pri_res = agent_responses.get("priority", {})
        inv_res = agent_responses.get("inventory", {})
        notif_res = agent_responses.get("notification", {})
        
        facilities = inv_res.get('recommended_facilities', [])
        fac_name = "Unknown Facility"
        fac_addr = ""
        fac_dist = "N/A"
        fac_units = 0
        blood_group = "Unknown"
        component = "Unknown"
        
        if facilities and isinstance(facilities, list) and len(facilities) > 0:
            first_fac = facilities[0]
            fac_name = first_fac.get("facility_name", fac_name)
            fac_addr = first_fac.get("facility_address", "")
            fac_dist = first_fac.get("distance_km", "Unknown")
            fac_units = first_fac.get("available_units", 0)
            blood_group = first_fac.get("blood_group", "Unknown")
            component = first_fac.get("component_type", "Unknown")
        
        pri_label = pri_res.get("priority_label", "⚪ Not Evaluated")
        pri_reason = pri_res.get("reason", "Standard protocol applies.")
        
        inv_summary = inv_res.get("summary", "No inventory data.")
        notif_action = notif_res.get("action_taken", "Not triggered.")
        
        clinical_summary = {
            "summary": f"Based on the request: '{user_request}', this patient requires immediate clinical intervention.",
            "priority": {
                "label": pri_label,
                "reason": f"{pri_reason}\n\nImmediate transfusion is clinically recommended to stabilize the patient's hemodynamic status."
            },
            "inventory": {
                "blood_group": blood_group,
                "component": component,
                "available_units": fac_units,
                "explanation": f"{inv_summary}\n\nThe available units must be managed carefully. Additional units may need to be sourced."
            },
            "facility": {
                "name": fac_name,
                "address": fac_addr,
                "distance_km": fac_dist,
                "reason": "Because this facility can respond quickly, it has been selected as the primary dispatch location."
            },
            "recommendation": f"Dispatch blood immediately from {fac_name}. Ensure transport protocols maintain proper temperature controls.",
            "donor_notification": f"{notif_action}\n\nNearby eligible donors should be notified if active inventory falls below emergency thresholds.",
            "clinical_risks": "Without rapid blood replacement, the patient is at severe risk of hypovolemic shock, multi-organ failure, cardiac arrest, and death.",
            "overall": "This is a critical emergency. Immediately reserve all compatible units and dispatch blood."
        }
        
        markdown_mock = f"""### 🚨 Clinical Assessment\n{clinical_summary['summary']}
\n### ⚖ Priority Explanation\n**{pri_label}**\n{clinical_summary['priority']['reason']}
\n### 🩸 Blood Availability\n{clinical_summary['inventory']['explanation']}
\n### 🏥 Recommended Facilities\n**{fac_name}**\n- Distance: {fac_dist} km\n- Available Units: {fac_units}\n{clinical_summary['facility']['reason']}
\n### 🚑 Dispatch Recommendation\n{clinical_summary['recommendation']}
\n### 👥 Donor Mobilisation\n{clinical_summary['donor_notification']}
\n### ⚠ Clinical Risks\n{clinical_summary['clinical_risks']}
\n### 📋 Immediate Action Plan\n1. Begin emergency transfusion protocol.\n2. Reserve all available compatible units.\n3. Dispatch blood immediately.\n4. Continue monitoring haemodynamic status.
\n### 🎯 Overall Recommendation\n{clinical_summary['overall']}"""
        
        return {"clinical_summary": clinical_summary, "final_answer": markdown_mock}

    prompt = (
        "You are the BloodLink AI Clinical Copilot, a senior transfusion medicine specialist assisting clinicians during emergencies.\n\n"
        "Using the user's request and the agent outputs below, generate a structured clinical recommendation.\n\n"
        f"User Request: {user_request}\n\n"
        f"Raw Agent Data: {json.dumps(agent_responses)}\n\n"
        "IMPORTANT RULES:\n"
        "1. NEVER return markdown alone. ALWAYS return a valid JSON object matching the SCHEMA below.\n"
        "2. NEVER use technical terms like 'Mock inventory', 'Delegated agent', 'Workflow', 'Success', 'JSON', 'Priority Agent', etc.\n"
        "3. Analyze the user's clinical condition (e.g. Massive Hemorrhage -> Tier 1 Immediate) and explicitly state the reasoning.\n"
        "4. Interpret the blood inventory logically. If only 1 unit is available for massive hemorrhage, state it is insufficient and recommend immediate external sourcing.\n"
        "5. Explain blood compatibility (e.g. O- preferred, O+ as alternative for males/non-childbearing under emergency protocol).\n"
        "6. Recommend nearest facilities and explain why they were selected (e.g. distance, travel time, stock).\n"
        "7. Formulate a risk assessment detailing the clinical risks of not acting rapidly.\n\n"
        "SCHEMA:\n"
        "{\n"
        '  "clinical_summary": {\n'
        '    "summary": "Concise summary of patient condition and needs",\n'
        '    "priority": {"label": "Priority Label with Emoji (e.g., 🔴 Critical)", "reason": "Detailed explanation of priority"},\n'
        '    "inventory": {"blood_group": "...", "component": "...", "available_units": 0, "explanation": "Contextual explanation of availability"},\n'
        '    "facility": {"name": "...", "address": "...", "distance_km": 0.0, "reason": "Why this facility was selected"},\n'
        '    "recommendation": "Actionable guidance (reserve units, prepare cross-matching, etc.)",\n'
        '    "donor_notification": "Donor mobilisation strategy based on inventory",\n'
        '    "clinical_risks": "Risks of delayed treatment",\n'
        '    "overall": "Executive summary recommendation"\n'
        '  },\n'
        '  "final_answer": "The full, rich Markdown narrative containing all sections (Clinical Assessment, Priority Explanation, Blood Availability, Recommended Facilities, Dispatch Recommendation, Donor Mobilisation, Clinical Risks, Immediate Action Plan, Overall Recommendation)"\n'
        "}\n\n"
        "Do NOT wrap the JSON in markdown code blocks like ```json."
    )
    
    response_text = ""
    try:
        response_text = ai_client.generate(
            prompt=prompt,
            agent_name="supervisor",
            system_instruction="You are a clinical AI. Output MUST be ONLY the requested JSON schema."
        ).strip()
        
        # Clean up potential markdown formatting from LLM
        if response_text.startswith("```json"):
            response_text = response_text[7:-3].strip()
        elif response_text.startswith("```"):
            response_text = response_text[3:-3].strip()
            
        final_json = json.loads(response_text)
        logger.info("Successfully generated structured clinical synthesis.")
        return final_json
        
    except Exception as e:
        logger.error(f"Failed to synthesize clinical JSON: {e}")
        logger.error(f"Response text was: {response_text}")
        
        fallback_markdown = "### 🚨 Clinical Assessment\n\nSystem encountered an error generating the clinical summary.\n\nPlease manually review the patient's request."
        fallback_summary = {
            "summary": "Error generating summary.",
            "priority": {"label": "Unknown", "reason": "Error parsing priority."},
            "inventory": {"blood_group": "Unknown", "component": "Unknown", "available_units": 0, "explanation": "Error checking inventory."},
            "facility": {"name": "Unknown", "address": "Unknown", "distance_km": 0.0, "reason": "Error analyzing facility."},
            "recommendation": "Manual review required.",
            "donor_notification": "Manual review required.",
            "clinical_risks": "Manual review required.",
            "overall": "Manual review required."
        }
        return {"clinical_summary": fallback_summary, "final_answer": fallback_markdown}

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
            # Step 0: Clinical NLP Extraction
            logger.info("Step 0: Extracting Clinical NLP Parameters.")
            nlp_prompt = (
                f"User Request: '{user_request}'\n\n"
                "Extract the following clinical entities from the request:\n"
                "1. condition (e.g. 'Massive Hemorrhage', 'Thalassemia', 'Unknown')\n"
                "2. blood_group (e.g. 'O-', 'A+', 'Unknown')\n"
                "3. facility_name (e.g. 'Central Hospital', 'Unknown')\n"
                "4. priority_tier (e.g. 'TIER_1_IMMEDIATE', 'TIER_2_URGENT', 'TIER_3_SCHEDULED', 'TIER_4_ELECTIVE')\n"
                "5. severity (e.g. 'Critical', 'High', 'Medium', 'Low')\n"
                "Return ONLY a valid JSON object with these keys. Do not include markdown."
            )
            
            if settings.USE_MOCK_AI:
                # Basic mock extraction based on keywords to bypass LLM while preserving real DB logic
                req_lower = user_request.lower()
                extracted = {
                    "condition": "Massive Hemorrhage" if "hemorrhage" in req_lower else "Unknown",
                    "blood_group": "O-" if "o-" in req_lower else "Unknown",
                    "facility_name": "Central Hospital" if "central hospital" in req_lower else "Unknown",
                    "priority_tier": "TIER_1_IMMEDIATE" if "hemorrhage" in req_lower or "accident" in req_lower else "TIER_2_URGENT",
                    "severity": "Critical" if "hemorrhage" in req_lower else "High"
                }
            else:
                try:
                    nlp_res_text = ai_client.generate(prompt=nlp_prompt, agent_name="supervisor")
                    if nlp_res_text.startswith("```json"): nlp_res_text = nlp_res_text[7:-3]
                    elif nlp_res_text.startswith("```"): nlp_res_text = nlp_res_text[3:-3]
                    extracted = json.loads(nlp_res_text.strip())
                except Exception as e:
                    logger.warning(f"Failed to parse NLP extraction: {e}")
                    extracted = {}
                    
            logger.info(f"Extracted NLP Context: {extracted}")
            
            # Merge extracted NLP data into context_params
            if extracted.get("blood_group") and extracted.get("blood_group") != "Unknown":
                context_params["blood_group"] = extracted.get("blood_group")
            if extracted.get("condition") and extracted.get("condition") != "Unknown":
                context_params["patient_condition"] = extracted.get("condition")
            if extracted.get("facility_name") and extracted.get("facility_name") != "Unknown":
                context_params["location"] = extracted.get("facility_name")
            if extracted.get("priority_tier") and extracted.get("priority_tier") != "Unknown":
                context_params["requested_priority"] = extracted.get("priority_tier")
                
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
            logger.info(f"Complete context sent to specialized agents: {json.dumps(context_params)}")
            
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
                            component_type=context_params.get("component_type"),
                            latitude=context_params.get("latitude"),
                            longitude=context_params.get("longitude"),
                            required_units=context_params.get("required_units"),
                            context_params=context_params
                        )
                    elif agent_name == "eligibility":
                        resp = agent.execute(
                            user_request=user_request,
                            donor_id=context_params.get("donor_id"),
                            manual_params=context_params.get("manual_params"),
                            context_params=context_params
                        )
                    elif agent_name == "priority":
                        resp = agent.execute(
                            user_request=user_request,
                            request_id=context_params.get("request_id"),
                            patient_condition=context_params.get("patient_condition", ""),
                            hemodynamic_status=context_params.get("hemodynamic_status", ""),
                            context_params=context_params
                        )
                    elif agent_name == "recommendation":
                        resp = agent.execute(
                            user_request=user_request,
                            blood_group=context_params.get("blood_group"), 
                            component_type=context_params.get("component_type"),
                            latitude=context_params.get("latitude"),
                            longitude=context_params.get("longitude"),
                            required_units=context_params.get("required_units"),
                            context_params=context_params
                        )
                    elif agent_name == "notification":
                        urgency_str = str(context_params.get("requested_priority", "medium")).lower()
                        resp = agent.execute(
                            user_request=user_request,
                            blood_group=context_params.get("blood_group"),
                            urgency=urgency_str,
                            location=context_params.get("location"),
                            inventory_available=context_params.get("inventory_available", False),
                            context_params=context_params
                        )
                    else:
                        resp = {"status": "Unknown Agent", "data": None}
                        
                    agent_responses[agent_name] = resp
                    logger.info(f"Response from {agent_name} agent: {json.dumps(resp)}")
                    logger.info(f"{agent_name.capitalize()} Agent execution complete.")
                    
                except Exception as ex:
                    logger.error(f"Error executing {agent_name} agent: {ex}")
                    agent_responses[agent_name] = {"error": str(ex)}

            # 3. Merge Responses
            logger.info("Step 3: Supervisor building final answer locally.")
            final_answer = build_final_answer(agent_responses, user_request)
            
            logger.info("Orchestrator workflow complete.")
            
            response = {
                "status": "Success",
                "user_request": user_request,
                "agents_involved": agents_to_call,
                "agent_data": agent_responses,
                "inventory_data": agent_responses.get("inventory", {})
            }
            # Merge final answer fields into root response
            response.update(final_answer)
            logger.info(f"Final synthesis object: {json.dumps(response)}")
            return response
            
        except Exception as e:
            logger.error(f"Orchestrator encountered a critical error: {e}", exc_info=True)
            return {
                "status": "Error",
                "user_request": user_request,
                "error": str(e),
                "final_answer": "System encountered an error while orchestrating the request."
            }
