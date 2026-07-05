"""
Priority Skill for BloodLink AI.
Determines blood request priority based on WHO triage guidelines.
"""

from typing import Dict, Any, Optional
from skills.shared_models import PriorityDecision
from database.queries import BloodQueries
from utils.logger import logger

class PrioritySkill:
    def __init__(self):
        self.queries = BloodQueries()

    def evaluate_request(self, request_id: int) -> PriorityDecision:
        """
        Evaluate priority for an existing database request.
        """
        logger.info(f"Evaluating priority for request ID: {request_id}")
        try:
            db = self.queries.db
            with db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM BloodRequest WHERE id = ?", (request_id,))
                row = cursor.fetchone()
                
            if not row:
                return PriorityDecision(
                    status="Error",
                    reason="Request not found in database.",
                    metadata={"request_id": request_id}
                )
                
            # Use explanation or patient_category if available to evaluate condition
            condition = row.get('explanation') or ""
            return self.evaluate_condition(condition)
        except Exception as e:
            logger.error(f"Error evaluating priority for request {request_id}: {e}")
            return PriorityDecision(
                status="Error",
                reason=f"Internal evaluation error: {str(e)}",
                metadata={"request_id": request_id}
            )

    def evaluate_condition(self, patient_condition: str, hemodynamic_status: str = "") -> PriorityDecision:
        """
        Evaluate priority manually using clinical text.
        """
        logger.info(f"Evaluating clinical condition: {patient_condition} | {hemodynamic_status}")
        
        condition = (patient_condition + " " + hemodynamic_status).lower()
        
        # Tier 1 rules
        if any(k in condition for k in ["birthing mother", "maternal", "active hemorrhage", "shock", "trauma", "immediate"]):
            tier = "TIER_1_IMMEDIATE"
            rationale = "Immediate life-saving intervention required for acute blood loss or shock."
            action = "Dispatch blood immediately via fastest available transport."
            eta = "< 15 minutes"
        # Tier 2 rules
        elif any(k in condition for k in ["heart failure", "hemodynamic instability", "acute thalassemia", "urgent", "thalassemia"]):
            # Note: "Routine Thalassemia" is caught below if explicitly 'routine'
            if "routine" not in condition:
                tier = "TIER_2_URGENT"
                rationale = "Urgent need to prevent severe morbidity or mortality."
                action = "Prepare blood and dispatch within 1 hour."
                eta = "< 1 hour"
            else:
                tier = "TIER_3_SCHEDULED"
                rationale = "Chronic condition requiring regular scheduled transfusions."
                action = "Schedule and reserve units for planned date."
                eta = "24-48 hours"
        # Tier 3 rules
        elif any(k in condition for k in ["routine thalassemia", "scheduled transfusion", "routine"]):
            tier = "TIER_3_SCHEDULED"
            rationale = "Chronic condition requiring regular scheduled transfusions."
            action = "Schedule and reserve units for planned date."
            eta = "24-48 hours"
        # Tier 4 rules
        elif "elective surgery" in condition or "elective" in condition:
            tier = "TIER_4_ELECTIVE"
            rationale = "Planned procedure; blood should be typed and cross-matched in advance."
            action = "Reserve units per surgical schedule."
            eta = "Scheduled date"
        else:
            # Default to TIER_3 if it doesn't match extremes
            tier = "TIER_3_SCHEDULED"
            rationale = "Standard blood request based on clinical judgment without critical indicators."
            action = "Process request normally and allocate available inventory."
            eta = "24-48 hours"

        explanation = f"Patient condition '{patient_condition}' maps to {tier}. WHO Rationale: {rationale}"
        
        return PriorityDecision(
            status=tier,
            reason=explanation,
            metadata={
                "Priority_tier": tier,
                "Reason": patient_condition,
                "WHO_rationale": rationale,
                "Recommended_action": action,
                "Estimated_response_time": eta
            }
        )
