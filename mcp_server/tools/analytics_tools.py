"""
MCP Tools for Analytics and Dashboarding.
"""

from typing import Dict, Any
from mcp_server.registry import registry
from database.queries import BloodQueries
from database.database import DatabaseManager
from utils.logger import logger

queries = BloodQueries()

@registry.register()
def dashboard() -> Dict[str, Any]:
    """Get overall dashboard statistics."""
    logger.info("Tool called: dashboard()")
    try:
        stats = queries.get_dashboard_statistics()
        return {"status": "success", "data": stats}
    except Exception as e:
        logger.error(f"dashboard error: {e}")
        return {"status": "error", "message": str(e)}

@registry.register()
def inventory_dashboard() -> Dict[str, Any]:
    """Get a detailed inventory dashboard including component types and expirations."""
    logger.info("Tool called: inventory_dashboard()")
    try:
        db = DatabaseManager()
        query = """
            SELECT component_type, blood_group, SUM(units_available) as total_units, SUM(reserved_units) as reserved
            FROM BloodInventory
            GROUP BY component_type, blood_group
            ORDER BY component_type, blood_group
        """
        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            results = [dict(row) for row in cursor.fetchall()]
        return {"status": "success", "data": results}
    except Exception as e:
        logger.error(f"inventory_dashboard error: {e}")
        return {"status": "error", "message": str(e)}

@registry.register()
def blood_group_summary() -> Dict[str, Any]:
    """Get a summary of available blood units grouped by blood group."""
    logger.info("Tool called: blood_group_summary()")
    try:
        db = DatabaseManager()
        query = """
            SELECT blood_group, SUM(units_available) as total_units
            FROM BloodInventory
            GROUP BY blood_group
            ORDER BY total_units DESC
        """
        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            results = [dict(row) for row in cursor.fetchall()]
        return {"status": "success", "data": results}
    except Exception as e:
        logger.error(f"blood_group_summary error: {e}")
        return {"status": "error", "message": str(e)}

@registry.register()
def daily_requests() -> Dict[str, Any]:
    """Get the number of requests made per day for the last 30 days."""
    logger.info("Tool called: daily_requests()")
    try:
        db = DatabaseManager()
        query = """
            SELECT date(request_date) as request_day, COUNT(*) as request_count
            FROM BloodRequest
            WHERE request_date >= date('now', '-30 days')
            GROUP BY request_day
            ORDER BY request_day DESC
        """
        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            results = [dict(row) for row in cursor.fetchall()]
        return {"status": "success", "data": results}
    except Exception as e:
        logger.error(f"daily_requests error: {e}")
        return {"status": "error", "message": str(e)}

@registry.register()
def blood_demand_trend() -> Dict[str, Any]:
    """Get blood demand trend over time."""
    logger.info("Tool called: blood_demand_trend()")
    try:
        db = DatabaseManager()
        query = """
            SELECT strftime('%Y-%m', request_date) as month, blood_group, SUM(requested_units) as total_requested
            FROM BloodRequest
            GROUP BY month, blood_group
            ORDER BY month DESC, total_requested DESC
            LIMIT 50
        """
        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            results = [dict(row) for row in cursor.fetchall()]
        return {"status": "success", "data": results}
    except Exception as e:
        logger.error(f"blood_demand_trend error: {e}")
        return {"status": "error", "message": str(e)}

@registry.register()
def donation_trend() -> Dict[str, Any]:
    """Get donation trend over time."""
    logger.info("Tool called: donation_trend()")
    try:
        db = DatabaseManager()
        query = """
            SELECT strftime('%Y-%m', donation_date) as month, COUNT(*) as total_donations
            FROM DonationHistory
            GROUP BY month
            ORDER BY month DESC
            LIMIT 12
        """
        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            results = [dict(row) for row in cursor.fetchall()]
        return {"status": "success", "data": results}
    except Exception as e:
        logger.error(f"donation_trend error: {e}")
        return {"status": "error", "message": str(e)}

@registry.register()
def low_stock_facilities() -> Dict[str, Any]:
    """Get a list of facilities that are running low on stock."""
    logger.info("Tool called: low_stock_facilities()")
    try:
        db = DatabaseManager()
        query = """
            SELECT hf.name as facility_name, bi.blood_group, bi.component_type, bi.units_available, bi.minimum_threshold
            FROM BloodInventory bi
            JOIN HealthcareFacility hf ON bi.facility_id = hf.id
            WHERE bi.units_available <= bi.minimum_threshold
            ORDER BY bi.units_available ASC
        """
        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            results = [dict(row) for row in cursor.fetchall()]
        return {"status": "success", "data": results}
    except Exception as e:
        logger.error(f"low_stock_facilities error: {e}")
        return {"status": "error", "message": str(e)}

@registry.register()
def low_stock_hospitals() -> Dict[str, Any]:
    """Alias for low_stock_facilities to match requested specific terminology."""
    return low_stock_facilities()

@registry.register()
def active_emergencies() -> Dict[str, Any]:
    """Get a list of all currently active emergency events."""
    logger.info("Tool called: active_emergencies()")
    try:
        db = DatabaseManager()
        query = """
            SELECT * FROM EmergencyEvent 
            WHERE is_active = 1
            ORDER BY declared_at DESC
        """
        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            results = [dict(row) for row in cursor.fetchall()]
        return {"status": "success", "data": results}
    except Exception as e:
        logger.error(f"active_emergencies error: {e}")
        return {"status": "error", "message": str(e)}

@registry.register()
def emergency_requests() -> Dict[str, Any]:
    """Get all immediate or urgent tier emergency requests."""
    logger.info("Tool called: emergency_requests()")
    try:
        db = DatabaseManager()
        query = """
            SELECT * FROM BloodRequest 
            WHERE requested_priority IN ('TIER_1_IMMEDIATE', 'TIER_2_URGENT')
              AND status = 'Pending'
            ORDER BY request_date ASC
        """
        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            results = [dict(row) for row in cursor.fetchall()]
        return {"status": "success", "data": results}
    except Exception as e:
        logger.error(f"emergency_requests error: {e}")
        return {"status": "error", "message": str(e)}

@registry.register()
def who_priority_statistics() -> Dict[str, Any]:
    """Get statistics of blood requests grouped by WHO priority tiers."""
    logger.info("Tool called: who_priority_statistics()")
    try:
        db = DatabaseManager()
        query = """
            SELECT requested_priority, COUNT(*) as count
            FROM BloodRequest
            GROUP BY requested_priority
            ORDER BY 
              CASE requested_priority
                WHEN 'TIER_1_IMMEDIATE' THEN 1
                WHEN 'TIER_2_URGENT' THEN 2
                WHEN 'TIER_3_SCHEDULED' THEN 3
                WHEN 'TIER_4_ELECTIVE' THEN 4
                ELSE 5
              END
        """
        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            results = [dict(row) for row in cursor.fetchall()]
        return {"status": "success", "data": results}
    except Exception as e:
        logger.error(f"who_priority_statistics error: {e}")
        return {"status": "error", "message": str(e)}

@registry.register()
def notification_statistics() -> Dict[str, Any]:
    """Generate statistics for notifications and donor responses."""
    logger.info("Tool called: notification_statistics()")
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
        logger.error(f"notification_statistics error: {e}")
        return {"status": "error", "message": str(e)}
