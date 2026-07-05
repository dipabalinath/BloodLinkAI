"""
MCP Tools for Notification Management.
"""

from typing import Dict, Any, List, Optional
from mcp_server.registry import registry
from database.queries import BloodQueries
from database.database import DatabaseManager
from utils.logger import logger

queries = BloodQueries()

# RBC Compatibility Map (Receiver: [Compatible Donors])
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

def _mock_send_sms(phone: str, message: str) -> bool:
    """Mock sending an SMS."""
    logger.info(f"[MOCK SMS] Sending to {phone}: {message}")
    return True

def _mock_send_email(email: str, message: str) -> bool:
    """Mock sending an Email."""
    logger.info(f"[MOCK EMAIL] Sending to {email}: {message}")
    return True

@registry.register()
def find_and_notify_compatible_donors(receiver_blood_group: str, facility_id: int, message: str, delivery_channel: str = 'SMS', limit: int = 10) -> Dict[str, Any]:
    """Find compatible, available, and eligible donors and notify them."""
    logger.info(f"Tool called: find_and_notify_compatible_donors({receiver_blood_group})")
    try:
        db = DatabaseManager()
        target_groups = COMPATIBILITY_MAP.get(receiver_blood_group, [receiver_blood_group])
        placeholders = ', '.join(['?'] * len(target_groups))
        
        query = f"""
            SELECT id FROM Donor
            WHERE blood_group IN ({placeholders})
              AND availability_status = 'Available'
              AND (eligible_after IS NULL OR eligible_after <= date('now'))
            LIMIT ?
        """
        params = tuple(target_groups) + (limit,)
        
        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            donor_rows = cursor.fetchall()
            
        donor_ids = [row['id'] for row in donor_rows]
        if not donor_ids:
            return {"status": "success", "message": "No eligible compatible donors found.", "data": []}
            
        return notify_multiple_donors(donor_ids, facility_id, "Urgent Request", message, delivery_channel)
    except Exception as e:
        logger.error(f"find_and_notify_compatible_donors error: {e}")
        return {"status": "error", "message": str(e)}

@registry.register()
def notify_donor(donor_id: int, facility_id: int, notification_type: str, message: str, delivery_channel: str = 'SMS') -> Dict[str, Any]:
    """Send a notification to a single donor."""
    logger.info(f"Tool called: notify_donor({donor_id}) via {delivery_channel}")
    try:
        donor = queries.get_donor(donor_id)
        if not donor:
            return {"status": "error", "message": "Donor not found."}

        # Store in Notification table
        notification_id = queries.create_notification(
            donor_id=donor_id,
            facility_id=facility_id,
            notification_type=notification_type,
            message=message,
            recipient_type="Donor",
            delivery_channel=delivery_channel
        )

        # Mock delivery
        delivery_status = "Failed"
        if delivery_channel.upper() == 'SMS' and donor.get('phone'):
            if _mock_send_sms(donor['phone'], message):
                delivery_status = "Sent"
        elif delivery_channel.upper() == 'EMAIL' and donor.get('email'):
            if _mock_send_email(donor['email'], message):
                delivery_status = "Sent"
        else:
            logger.warning(f"Donor {donor_id} lacks contact info for channel {delivery_channel}")

        # Update delivery status
        db = DatabaseManager()
        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE Notification SET delivery_status = ?, sent_at = CURRENT_TIMESTAMP WHERE id = ?", (delivery_status, notification_id))
            conn.commit()

        return {
            "status": "success", 
            "data": {
                "notification_id": notification_id,
                "delivery_status": delivery_status
            }
        }
    except Exception as e:
        logger.error(f"notify_donor error: {e}")
        return {"status": "error", "message": str(e)}

@registry.register()
def notify_multiple_donors(donor_ids: List[int], facility_id: int, notification_type: str, message: str, delivery_channel: str = 'SMS') -> Dict[str, Any]:
    """Send notifications to multiple donors."""
    logger.info(f"Tool called: notify_multiple_donors({len(donor_ids)} donors) via {delivery_channel}")
    try:
        results = []
        for d_id in donor_ids:
            res = notify_donor(d_id, facility_id, notification_type, message, delivery_channel)
            results.append({"donor_id": d_id, "result": res})
            
        success_count = sum(1 for r in results if r['result'].get('status') == 'success' and r['result']['data']['delivery_status'] == 'Sent')
        
        return {
            "status": "success",
            "message": f"Successfully notified {success_count} out of {len(donor_ids)} donors.",
            "data": results
        }
    except Exception as e:
        logger.error(f"notify_multiple_donors error: {e}")
        return {"status": "error", "message": str(e)}

@registry.register()
def save_response(notification_id: int, donor_id: int, response_type: str, additional_notes: Optional[str] = None) -> Dict[str, Any]:
    """Save a donor's response to a notification (e.g., Accepted, Declined)."""
    logger.info(f"Tool called: save_response({notification_id}, {response_type})")
    try:
        db = DatabaseManager()
        query = """
            INSERT INTO DonorNotificationResponse (notification_id, donor_id, response_type, additional_notes)
            VALUES (?, ?, ?, ?)
        """
        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (notification_id, donor_id, response_type, additional_notes))
            
            # Also update the notification record's response field for quick access
            cursor.execute("UPDATE Notification SET response = ? WHERE id = ?", (response_type, notification_id))
            conn.commit()
            
            return {"status": "success", "message": f"Response '{response_type}' saved successfully."}
    except Exception as e:
        logger.error(f"save_response error: {e}")
        return {"status": "error", "message": str(e)}

@registry.register()
def get_pending_notifications() -> Dict[str, Any]:
    """Get all notifications that haven't been responded to or delivered successfully."""
    logger.info("Tool called: get_pending_notifications()")
    try:
        db = DatabaseManager()
        query = """
            SELECT * FROM Notification 
            WHERE response IS NULL OR delivery_status = 'Pending'
            ORDER BY created_at DESC
        """
        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            results = [dict(row) for row in cursor.fetchall()]
            
        return {"status": "success", "data": results}
    except Exception as e:
        logger.error(f"get_pending_notifications error: {e}")
        return {"status": "error", "message": str(e)}

@registry.register()
def get_notification_statistics() -> Dict[str, Any]:
    """Generate statistics for notifications and donor responses."""
    logger.info("Tool called: get_notification_statistics()")
    try:
        db = DatabaseManager()
        stats = {
            "total_sent": 0,
            "delivery_status": {},
            "responses": {}
        }
        
        with db.connect() as conn:
            cursor = conn.cursor()
            
            # Delivery stats
            cursor.execute("SELECT delivery_status, COUNT(*) as count FROM Notification GROUP BY delivery_status")
            for row in cursor.fetchall():
                stats['delivery_status'][row['delivery_status'] or 'Unknown'] = row['count']
                stats['total_sent'] += row['count']
                
            # Response stats
            cursor.execute("SELECT response_type, COUNT(*) as count FROM DonorNotificationResponse GROUP BY response_type")
            for row in cursor.fetchall():
                stats['responses'][row['response_type'] or 'Unknown'] = row['count']
                
        return {"status": "success", "data": stats}
    except Exception as e:
        logger.error(f"get_notification_statistics error: {e}")
        return {"status": "error", "message": str(e)}
