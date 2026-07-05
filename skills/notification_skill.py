"""
Notification Skill for BloodLink AI.
Handles generation and preparation of personalized donor notifications.
"""

from typing import Dict, Any, List
from skills.shared_models import NotificationResult
from database.database import DatabaseManager
from utils.logger import logger
from datetime import datetime

class NotificationSkill:
    def prepare_notification(self, blood_group: str, urgency: str, location: str, limit: int = 10) -> NotificationResult:
        """
        Prepare notifications by finding priority donors and generating messages.
        Prioritizes: registered, eligible, compatible, last donation >= 90 days.
        """
        logger.info(f"Preparing notification for {blood_group} at {location}")
        try:
            # Use the DatabaseManager to query donors with priorities
            db = DatabaseManager()
            
            # Map of compatible groups
            COMPATIBILITY_MAP = {
                'AB+': ['AB+', 'AB-', 'A+', 'A-', 'B+', 'B-', 'O+', 'O-'],
                'AB-': ['AB-', 'A-', 'B-', 'O-'],
                'A+': ['A+', 'A-', 'O+', 'O-'],
                'A-': ['A-', 'O-'],
                'B+': ['B+', 'B-', 'O+', 'O-'],
                'B-': ['B-', 'O-'],
                'O+': ['O+', 'O-'],
                'O-': ['O-']
            }
            
            target_groups = COMPATIBILITY_MAP.get(blood_group, [blood_group])
            placeholders = ', '.join(['?'] * len(target_groups))
            
            # Query prioritizing last_donation_date <= 90 days ago and eligible
            query = f"""
                SELECT * FROM Donor
                WHERE blood_group IN ({placeholders})
                  AND availability_status = 'Available'
                  AND (eligible_after IS NULL OR eligible_after <= date('now'))
                  AND (last_donation_date IS NULL OR last_donation_date <= date('now', '-90 days'))
                ORDER BY 
                  CASE WHEN blood_group = ? THEN 1 ELSE 2 END,
                  last_donation_date ASC
                LIMIT ?
            """
            
            params = tuple(target_groups) + (blood_group, limit)
            
            with db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                donors = [dict(row) for row in cursor.fetchall()]
                
            if not donors:
                return NotificationResult(
                    status="No Donors Found",
                    reason="Could not find any eligible compatible donors meeting criteria.",
                    metadata={"donors_targeted": 0}
                )
                
            prepared_messages = []
            for donor in donors:
                prepared_messages.append({
                    "donor_id": donor['id'],
                    "name": donor.get('first_name', 'Hero'),
                    "blood_group": donor.get('blood_group'),
                    "sms": self.generate_sms(donor, urgency, location),
                    "email": self.generate_email(donor, urgency, location)
                })
                
            return NotificationResult(
                status="Success",
                reason=f"Prepared notifications for {len(donors)} donors.",
                metadata={
                    "donors_targeted": len(donors),
                    "messages": prepared_messages
                }
            )
            
        except Exception as e:
            logger.error(f"Error in prepare_notification: {e}")
            return NotificationResult(
                status="Error",
                reason=f"Internal error: {str(e)}"
            )

    def generate_sms(self, donor: Dict[str, Any], urgency: str, location: str) -> str:
        """Generate a personalized SMS message."""
        name = donor.get('first_name', 'Donor')
        bg = donor.get('blood_group', 'Blood')
        if urgency.lower() in ['immediate', 'urgent', 'high', 'tier_1_immediate', 'tier_2_urgent']:
            return f"URGENT: Hi {name}, a critical patient needs {bg} blood at {location}. Your donation can save a life today. Please reply YES if available."
        else:
            return f"BloodLink: Hi {name}, there is a need for {bg} blood at {location}. If you are able to donate, please visit us soon."

    def generate_email(self, donor: Dict[str, Any], urgency: str, location: str) -> str:
        """Generate a personalized Email message."""
        name = donor.get('first_name', 'Valued Donor')
        bg = donor.get('blood_group', 'Blood')
        last_donation = donor.get('last_donation_date')
        
        intro = f"Dear {name},\n\nWe hope this email finds you well."
        if last_donation:
            intro += f" Thank you for your previous donation on {last_donation}."
            
        if urgency.lower() in ['immediate', 'urgent', 'high', 'tier_1_immediate', 'tier_2_urgent']:
            body = (
                f"\n\nWe are reaching out with an URGENT request. A patient at {location} "
                f"is in critical need of {bg} blood. As a compatible donor, your help is urgently requested.\n"
                f"Please reply to this email or head directly to {location} if you can assist."
            )
        else:
            body = (
                f"\n\nThere is currently a need for {bg} blood at {location}. "
                f"Your continued support helps us maintain a stable blood supply and saves lives.\n"
                f"Please consider scheduling a donation at your earliest convenience."
            )
            
        footer = "\n\nThank you for being a hero.\nSincerely,\nThe BloodLink AI Team"
        
        return intro + body + footer
