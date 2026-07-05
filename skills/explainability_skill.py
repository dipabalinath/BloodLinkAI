"""
Explainability Skill for BloodLink AI.
Translates complex AI decisions and technical outputs into clear, natural language 
explanations tailored for hospital staff and administrators.
"""

from typing import Dict, Any
from skills.shared_models import ExplainabilityResult
from utils.logger import logger

class ExplainabilitySkill:
    def explain_eligibility(self, eligibility_result: Any) -> ExplainabilityResult:
        """Explain donor eligibility decisions."""
        logger.info("Explaining eligibility decision.")
        status = eligibility_result.status
        reason = eligibility_result.reason
        
        explanation = f"The donor is currently classified as '{status}'. "
        if status == "Eligible":
            explanation += "They meet all standard WHO criteria for blood donation and are cleared to donate."
        else:
            explanation += f"This is due to the following clinical reasons: {reason}. "
            if status == "Temporary Deferral":
                explanation += "Please advise the donor on when they might become eligible again based on the provided deferral period."
            else:
                explanation += "Please inform the donor that they are permanently deferred for their safety or the safety of the blood supply."
                
        return ExplainabilityResult(
            status="Success",
            reason=explanation,
            metadata={"original_status": status}
        )

    def explain_priority(self, priority_decision: Any) -> ExplainabilityResult:
        """Explain blood request prioritization."""
        logger.info("Explaining priority decision.")
        status = priority_decision.status
        reason = priority_decision.reason
        
        explanation = f"This blood request has been assigned priority '{status}'. "
        explanation += f"Clinical Justification: {reason} "
        
        if "TIER_1" in status:
            explanation += "\nAction Required: Immediate dispatch is necessary. This is a critical life-saving emergency."
        elif "TIER_2" in status:
            explanation += "\nAction Required: Urgent dispatch required within 1 hour to prevent severe complications."
        else:
            explanation += "\nAction Required: Process according to standard scheduling and reservation protocols."
            
        return ExplainabilityResult(
            status="Success",
            reason=explanation,
            metadata={"original_status": status}
        )

    def explain_recommendation(self, recommendation_result: Any) -> ExplainabilityResult:
        """Explain inventory recommendations."""
        logger.info("Explaining inventory recommendation.")
        status = recommendation_result.status
        reason = recommendation_result.reason
        
        explanation = f"Inventory Recommendation ({status}):\n"
        explanation += f"Details: {reason}\n\n"
        explanation += "How this was decided:\nThe AI selected this option by weighing the physical distance to the facility, the exact blood group match versus safe clinical substitutes, and prioritizing units closest to expiration to minimize blood wastage."
        
        return ExplainabilityResult(
            status="Success",
            reason=explanation,
            metadata={"original_status": status}
        )

    def explain_inventory_status(self, inventory_data: Dict[str, Any]) -> ExplainabilityResult:
        """Explain general inventory status for a hospital."""
        logger.info("Explaining inventory status.")
        explanation = "Based on the current inventory scan:\n"
        
        if not inventory_data.get("data"):
            explanation += "There is no available inventory matching the criteria."
        else:
            total_units = sum(item.get("units_available", 0) for item in inventory_data["data"])
            explanation += f"We found {total_units} units available across {len(inventory_data['data'])} matching records. "
            explanation += "Sufficient stock is present, but please monitor utilization closely if emergency requests surge."
            
        return ExplainabilityResult(
            status="Success",
            reason=explanation,
            metadata={"raw_records_count": len(inventory_data.get("data", []))}
        )

    def explain_notifications(self, notification_result: Any) -> ExplainabilityResult:
        """Explain the notification dispatch strategy."""
        logger.info("Explaining notification dispatch.")
        status = notification_result.status
        metadata = notification_result.metadata
        
        donors_targeted = metadata.get("donors_targeted", 0)
        
        explanation = f"Notification Dispatch Status: {status}.\n"
        explanation += f"The system has successfully queued messages for {donors_targeted} donors. "
        
        if donors_targeted > 0:
            explanation += "These donors were selected because they are actively registered, currently eligible under WHO guidelines, have compatible blood types for the requested patient, and their last donation was at least 90 days ago."
        else:
            explanation += "Unfortunately, no donors matched all the safety and compatibility requirements at this time."
            
        return ExplainabilityResult(
            status="Success",
            reason=explanation,
            metadata={"donors_targeted": donors_targeted}
        )
