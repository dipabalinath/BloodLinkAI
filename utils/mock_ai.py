import json
from typing import Dict, Any
from utils.logger import logger

def generate_mock_response(agent_name: str, prompt: str) -> Dict[str, Any]:
    """
    Generate deterministic mock responses for testing without calling Gemini.
    Returns dictionaries matching each agent's expected output format.
    """
    logger.info(f"Generating mock response for agent: {agent_name}")
    
    agent_name = agent_name.lower().strip()
    
    if agent_name == "eligibility":
        prompt_lower = prompt.lower()
        if any(term in prompt_lower for term in ["age below 18", "16 year", "17 year", "underweight", "low hemoglobin"]):
            return {
                "eligibility": "Temporary Deferral",
                "reason": "Does not meet minimum WHO criteria",
                "next_eligible_date": "2027-01-01",
                "explanation": "Donor is deferred based on age, weight, or hemoglobin levels."
            }
        else:
            return {
                "eligibility": "Eligible",
                "reason": "Meets all WHO criteria",
                "next_eligible_date": "N/A",
                "explanation": "Donor is fully eligible based on age, weight, and hemoglobin levels."
            }
        
    elif agent_name == "priority":
        user_request_line = ""
        for line in prompt.split('\n'):
            if line.startswith("User Request:"):
                user_request_line = line.lower()
                break
                
        if any(term in user_request_line for term in ["hemorrhage", "massive bleeding", "birthing mother"]):
            return {
                "priority": "TIER_1_IMMEDIATE",
                "reason": "Active hemorrhage or critical condition detected.",
                "who_explanation": "Under WHO triage rules, this requires immediate life-saving intervention (Tier 1)."
            }
        elif "thalassemia" in user_request_line:
            return {
                "priority": "TIER_3_ROUTINE",
                "reason": "Routine transfusion need.",
                "who_explanation": "Under WHO triage rules, routine scheduled transfusions map to Tier 3."
            }
        elif "elective surgery" in user_request_line:
            return {
                "priority": "TIER_4",
                "reason": "Elective surgery request.",
                "who_explanation": "Elective surgeries are lowest priority (Tier 4) according to WHO guidelines."
            }
        else:
            return {
                "priority": "TIER_2_URGENT",
                "reason": "Default urgent classification",
                "who_explanation": "Fell back to Tier 2."
            }
        
    elif agent_name == "inventory":
        return {
            "status": "Success",
            "summary": "Mock inventory search completed successfully.",
            "explanation": "Found 5 units of matching blood group in nearby facilities.",
            "recommended_facilities": [
                {"facility": "Central Hospital", "units": 5, "blood_group": "O-", "distance_sq": 2.5}
            ]
        }
        
    elif agent_name == "recommendation":
        return {
            "top_recommendation": {"facility": "Central Hospital", "blood_group": "O-", "units": 5},
            "alternatives": [
                {"facility": "North Clinic", "blood_group": "O-", "units": 2}
            ],
            "reasoning": "Central Hospital is closest and has sufficient stock of the exact blood group requested."
        }
        
    elif agent_name == "notification":
        return {
            "status": "Success",
            "donors_notified": 3,
            "sample_sms": "URGENT: Blood needed at Central Hospital. Please donate today.",
            "sample_email": "Dear Donor, your blood type is urgently needed at Central Hospital...",
            "summary": "Successfully targeted 3 eligible donors who haven't donated in 90 days."
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
