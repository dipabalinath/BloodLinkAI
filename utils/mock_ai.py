import json
from typing import Dict, Any, Optional
from utils.logger import logger

def generate_mock_response(agent_name: str, prompt: str, context_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Generate deterministic mock responses for testing without calling Gemini.
    Returns dictionaries matching each agent's expected output format using real context parameters.
    """
    logger.info(f"Generating contextual mock response for agent: {agent_name}")
    
    agent_name = agent_name.lower().strip()
    ctx = context_params or {}
    
    # Extract defaults from context_params
    blood_group = ctx.get("blood_group", "O-")
    component_type = ctx.get("component_type", "Packed RBC")
    req_units = ctx.get("required_units", 1)
    patient_condition = ctx.get("patient_condition", "Unknown condition")
    priority_tier = ctx.get("requested_priority", "TIER_2_URGENT")
    priority_label = "Immediate (Tier 1)" if priority_tier == "TIER_1_IMMEDIATE" else "High (Urgent)"
    
    # Safely extract from injected operational DB data
    raw_inventory = ctx.get("raw_inventory", [])
    rec_data = ctx.get("recommendation_data", {})
    options = rec_data.get("options", [])
    
    facility_name = "Unknown Facility"
    facility_address = "Mock Address, City"
    distance_km = 0.0
    actual_units = req_units
    
    if options:
        best_fac = options[0]
        facility_name = best_fac.get("facility_name", facility_name)
        facility_address = best_fac.get("facility_address", facility_address)
        distance_km = best_fac.get("distance_km", 0.0)
        actual_units = best_fac.get("available_units", req_units)
    elif raw_inventory:
        best_fac = raw_inventory[0]
        facility_name = best_fac.get("facility_name", facility_name)
        facility_address = best_fac.get("facility_address", facility_address)
        distance_km = best_fac.get("distance_km", 0.0)
        actual_units = best_fac.get("available_units", req_units)
        
    facility_name = ctx.get("location", facility_name) if facility_name == "Unknown Facility" else facility_name
    
    if agent_name == "eligibility":
        return {
            "status": "Success",
            "eligibility": "Eligible",
            "reason": "Mock donor meets all WHO criteria based on contextual parameters."
        }
        
    elif agent_name == "priority":
        return {
            "status": "Success",
            "priority_tier": priority_tier,
            "priority_label": priority_label,
            "reason": f"Mock assessed priority based on condition: {patient_condition}."
        }
        
    elif agent_name == "inventory":
        return {
            "status": "Success",
            "summary": f"Found {actual_units} units of {blood_group} {component_type}.",
            "explanation": f"Inventory search confirmed availability of {blood_group} at {facility_name}.",
            "recommended_facilities": [
                {
                    "facility_id": 1,
                    "facility_name": facility_name,
                    "facility_address": facility_address,
                    "available_units": actual_units,
                    "blood_group": blood_group,
                    "component_type": component_type,
                    "distance_km": distance_km
                }
            ]
        }
        
    elif agent_name == "recommendation":
        return {
            "status": "Success",
            "recommendation": f"Proceed with reservation of {req_units} units at {facility_name}."
        }
        
    elif agent_name == "notification":
        return {
            "status": "Success",
            "notification_required": True,
            "target_facility": facility_name,
            "blood_group": blood_group,
            "message": f"URGENT: Blood needed at {facility_name}. Please donate {blood_group}."
        }
        
    elif agent_name == "supervisor":
        return {
            "status": "success",
            "workflow_reasoning": "Delegated correctly.",
            "delegated_agents": [
                "priority",
                "inventory",
                "notification"
            ],
            "delegated_data": {},
            "final_answer": "..."
        }
        
    else:
        logger.warning(f"Unknown agent '{agent_name}' requested for mock response.")
        return {
            "status": "Error",
            "message": f"No mock response defined for agent: {agent_name}"
        }
