"""
Agent Factory for BloodLink AI.
Instantiates and returns all specialized agents as a dictionary.
"""

from agents.supervisor_agent import SupervisorAgent
from agents.inventory_agent import InventoryAgent
from agents.eligibility_agent import EligibilityAgent
from agents.priority_agent import PriorityAgent
from agents.recommendation_agent import RecommendationAgent
from agents.notification_agent import NotificationAgent
from utils.logger import logger

def get_agents() -> dict:
    """
    Instantiate and return all BloodLink agents.
    
    Returns:
        dict: A dictionary mapping agent names to their respective instances.
    """
    logger.info("Instantiating BloodLink AI Agents via Agent Factory.")
    
    agents = {
        "supervisor": SupervisorAgent(),
        "inventory": InventoryAgent(),
        "eligibility": EligibilityAgent(),
        "priority": PriorityAgent(),
        "recommendation": RecommendationAgent(),
        "notification": NotificationAgent()
    }
    
    logger.info("Successfully instantiated all agents.")
    return agents
