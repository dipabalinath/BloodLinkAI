"""
MCP Tools for Blood Request Management.
"""

from typing import Dict, Any, Optional, List
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

@registry.register()
def evaluate_who_priority(patient_condition: str, hemodynamic_status: str = "") -> Dict[str, Any]:
    """
    Evaluate the priority of a blood request based on WHO guidelines.
    """
    logger.info(f"Tool called: evaluate_who_priority({patient_condition}, {hemodynamic_status})")
    try:
        condition = (patient_condition + " " + hemodynamic_status).lower()
        
        if any(k in condition for k in ["birthing mother", "maternal", "active hemorrhage", "shock", "trauma"]):
            tier = "TIER_1_IMMEDIATE"
            rationale = "Immediate life-saving intervention required for acute blood loss or shock."
            eta = "< 15 minutes"
        elif any(k in condition for k in ["heart failure", "hemodynamic instability", "acute thalassemia"]):
            tier = "TIER_2_URGENT"
            rationale = "Urgent need to prevent severe morbidity or mortality."
            eta = "< 1 hour"
        elif "routine thalassemia" in condition or "thalassemia" in condition:
            tier = "TIER_3_SCHEDULED"
            rationale = "Chronic condition requiring regular scheduled transfusions."
            eta = "24-48 hours"
        elif "elective surgery" in condition or "elective" in condition:
            tier = "TIER_4_ELECTIVE"
            rationale = "Planned procedure; blood should be typed and cross-matched in advance."
            eta = "Scheduled date"
        else:
            tier = "TIER_3_SCHEDULED"
            rationale = "Standard blood request based on clinical judgment."
            eta = "24-48 hours"
            
        return {
            "status": "success",
            "data": {
                "Priority": tier,
                "Reason": patient_condition,
                "WHO_rationale": rationale,
                "Estimated_response_time": eta
            }
        }
    except Exception as e:
        logger.error(f"evaluate_who_priority error: {e}")
        return {"status": "error", "message": str(e)}

@registry.register()
def get_compatible_blood(blood_group: str) -> Dict[str, Any]:
    """Get compatible blood groups for a given receiver's blood group."""
    logger.info(f"Tool called: get_compatible_blood({blood_group})")
    compatible = COMPATIBILITY_MAP.get(blood_group, [blood_group])
    return {
        "status": "success", 
        "data": {
            "receiver_blood_group": blood_group,
            "compatible_donors": compatible
        }
    }

@registry.register()
def find_nearest_hospital(latitude: float, longitude: float, radius_km: float = 20.0) -> Dict[str, Any]:
    """Find the nearest healthcare facilities within a given radius."""
    logger.info(f"Tool called: find_nearest_hospital({latitude}, {longitude})")
    try:
        db = DatabaseManager()
        # Rough approximation: 1 degree latitude is ~111 km.
        degree_radius = radius_km / 111.0
        
        query = """
            SELECT *, 
                   ((latitude - ?) * (latitude - ?) + (longitude - ?) * (longitude - ?)) as distance_sq
            FROM HealthcareFacility
            WHERE latitude BETWEEN ? AND ? 
              AND longitude BETWEEN ? AND ?
            ORDER BY distance_sq ASC
            LIMIT 10
        """
        params = (
            latitude, latitude, longitude, longitude,
            latitude - degree_radius, latitude + degree_radius,
            longitude - degree_radius, longitude + degree_radius
        )
        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            results = [dict(row) for row in cursor.fetchall()]
        
        return {"status": "success", "data": results}
    except Exception as e:
        logger.error(f"find_nearest_hospital error: {e}")
        return {"status": "error", "message": str(e)}

@registry.register()
def find_best_inventory(blood_group: str, component_type: str, latitude: float, longitude: float, required_units: int, allow_substitutes: bool = True) -> Dict[str, Any]:
    """Find the best inventory including compatible blood groups and distance."""
    logger.info(f"Tool called: find_best_inventory({blood_group}, {component_type})")
    try:
        db = DatabaseManager()
        target_groups = COMPATIBILITY_MAP.get(blood_group, [blood_group]) if allow_substitutes else [blood_group]
        
        placeholders = ', '.join(['?'] * len(target_groups))
        query = f"""
            SELECT bi.*, hf.name as facility_name, hf.latitude, hf.longitude,
                   ((hf.latitude - ?) * (hf.latitude - ?) + (hf.longitude - ?) * (hf.longitude - ?)) as distance_sq
            FROM BloodInventory bi
            JOIN HealthcareFacility hf ON bi.facility_id = hf.id
            WHERE bi.blood_group IN ({placeholders}) 
              AND bi.component_type = ? 
              AND bi.units_available >= ?
            ORDER BY 
              CASE WHEN bi.blood_group = ? THEN 1 ELSE 2 END,
              distance_sq ASC
            LIMIT 10
        """
        params = (latitude, latitude, longitude, longitude) + tuple(target_groups) + (component_type, required_units, blood_group)
        
        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            results = [dict(row) for row in cursor.fetchall()]
            
        return {"status": "success", "data": results}
    except Exception as e:
        logger.error(f"find_best_inventory error: {e}")
        return {"status": "error", "message": str(e)}

@registry.register()
def create_request(
    patient_id: int, 
    requesting_facility_id: int, 
    blood_group: str, 
    component_type: str, 
    requested_units: int, 
    requested_priority: str,
    explanation: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new blood request."""
    logger.info(f"Tool called: create_request for patient {patient_id}")
    try:
        req_id = queries.create_blood_request(
            patient_id=patient_id,
            requesting_facility_id=requesting_facility_id,
            blood_group=blood_group,
            component_type=component_type,
            requested_units=requested_units,
            requested_priority=requested_priority,
            explanation=explanation
        )
        return {"status": "success", "data": {"request_id": req_id}}
    except Exception as e:
        logger.error(f"create_request error: {e}")
        return {"status": "error", "message": str(e)}

@registry.register()
def prioritize_request(request_id: int, ai_priority: int) -> Dict[str, Any]:
    """Update the AI priority tier for a blood request."""
    logger.info(f"Tool called: prioritize_request({request_id}, {ai_priority})")
    try:
        db = DatabaseManager()
        query = "UPDATE BloodRequest SET ai_priority = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (ai_priority, request_id))
            conn.commit()
            if cursor.rowcount > 0:
                return {"status": "success", "message": f"Updated AI priority for request {request_id}"}
            return {"status": "error", "message": "Request not found."}
    except Exception as e:
        logger.error(f"prioritize_request error: {e}")
        return {"status": "error", "message": str(e)}

@registry.register()
def find_nearest_inventory(blood_group: str, component_type: str, latitude: float, longitude: float, required_units: int) -> Dict[str, Any]:
    """Find the nearest available inventory."""
    logger.info(f"Tool called: find_nearest_inventory({blood_group}, {component_type})")
    try:
        results = queries.get_nearest_available_inventory(
            blood_group=blood_group,
            component_type=component_type,
            latitude=latitude,
            longitude=longitude,
            required_units=required_units
        )
        return {"status": "success", "data": results}
    except Exception as e:
        logger.error(f"find_nearest_inventory error: {e}")
        return {"status": "error", "message": str(e)}

@registry.register()
def reserve_inventory(request_id: int, inventory_id: int, units: int) -> Dict[str, Any]:
    """Reserve inventory for a specific request."""
    logger.info(f"Tool called: reserve_inventory({request_id}, {inventory_id}, {units})")
    try:
        db = DatabaseManager()
        success = queries.reserve_units(inventory_id, units)
        if success:
            query = """
                INSERT INTO Reservation (request_id, inventory_id, reserved_units, status)
                VALUES (?, ?, ?, 'Active')
            """
            with db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (request_id, inventory_id, units))
                conn.commit()
                reservation_id = cursor.lastrowid
                
            return {
                "status": "success", 
                "data": {"reservation_id": reservation_id},
                "message": f"Reserved {units} units for request {request_id}"
            }
        return {"status": "error", "message": "Failed to reserve units. Insufficient stock."}
    except Exception as e:
        logger.error(f"reserve_inventory error: {e}")
        return {"status": "error", "message": str(e)}

@registry.register()
def get_pending_requests() -> Dict[str, Any]:
    """Get all pending blood requests."""
    logger.info("Tool called: get_pending_requests()")
    try:
        requests = queries.get_pending_requests()
        return {"status": "success", "data": requests}
    except Exception as e:
        logger.error(f"get_pending_requests error: {e}")
        return {"status": "error", "message": str(e)}
