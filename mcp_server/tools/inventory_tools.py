"""
MCP Tools for Blood Inventory Management.
Provides structured, typed, and well-logged tools for interacting with BloodLink's inventory.
"""

from typing import Dict, Any, List, Optional
from mcp_server.registry import registry
from database.queries import BloodQueries
from database.database import DatabaseManager
from utils.logger import logger

queries = BloodQueries()

# RBC Compatibility Map (Receiver: [Compatible Donors])
COMPATIBILITY_MAP: Dict[str, List[str]] = {
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
def find_inventory(blood_group: str, component_type: str, minimum_units: int, allow_substitutes: bool = True) -> Dict[str, Any]:
    """
    Find available inventory matching the criteria.
    If exact match is unavailable and allow_substitutes is True, it searches for compatible blood groups.
    
    Args:
        blood_group (str): The requested blood group (e.g., 'O+').
        component_type (str): The blood component type (e.g., 'Packed RBC').
        minimum_units (int): Minimum required units available.
        allow_substitutes (bool): Whether to fallback to compatible blood groups.
        
    Returns:
        Dict[str, Any]: JSON dict containing status and resulting data.
    """
    logger.info(f"[INVENTORY_SEARCH] Requested: {blood_group} {component_type}, Min Units: {minimum_units}")
    try:
        db = DatabaseManager()
        
        # Determine target blood groups
        target_groups = [blood_group]
        if allow_substitutes and blood_group in COMPATIBILITY_MAP:
            target_groups = COMPATIBILITY_MAP[blood_group]
            
        placeholders = ', '.join(['?'] * len(target_groups))
        query = f"""
            SELECT bi.*, hf.name as facility_name 
            FROM BloodInventory bi
            JOIN HealthcareFacility hf ON bi.facility_id = hf.id
            WHERE bi.blood_group IN ({placeholders}) 
              AND bi.component_type = ? 
              AND bi.units_available >= ?
            ORDER BY 
              CASE WHEN bi.blood_group = ? THEN 1 ELSE 2 END,
              bi.units_available DESC
        """
        
        params = tuple(target_groups) + (component_type, minimum_units, blood_group)
        
        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            results = [dict(row) for row in cursor.fetchall()]
        
        logger.info(f"[INVENTORY_SEARCH] Found {len(results)} matching inventory records.")
        return {"status": "success", "data": results}
    except Exception as e:
        logger.error(f"[INVENTORY_SEARCH] Error: {str(e)}", exc_info=True)
        return {"status": "error", "message": f"Database error occurred: {str(e)}"}

@registry.register()
def reserve_units(inventory_id: int, units: int) -> Dict[str, Any]:
    """
    Reserve a specific number of blood units from a given inventory record.
    
    Args:
        inventory_id (int): ID of the BloodInventory record.
        units (int): Number of units to reserve.
        
    Returns:
        Dict[str, Any]: JSON dict containing the operation status.
    """
    logger.info(f"[RESERVE_UNITS] Attempting to reserve {units} units from Inventory ID: {inventory_id}")
    try:
        success = queries.reserve_units(inventory_id, units)
        if success:
            logger.info(f"[RESERVE_UNITS] Successfully reserved {units} units.")
            return {"status": "success", "message": f"Successfully reserved {units} units from inventory {inventory_id}"}
        
        logger.warning(f"[RESERVE_UNITS] Failed. Insufficient stock or invalid ID for inventory {inventory_id}.")
        return {"status": "error", "message": "Failed to reserve units. Insufficient stock or invalid ID."}
    except Exception as e:
        logger.error(f"[RESERVE_UNITS] Error: {str(e)}", exc_info=True)
        return {"status": "error", "message": f"Database error occurred: {str(e)}"}

@registry.register()
def release_reservation(reservation_id: int) -> Dict[str, Any]:
    """
    Release reserved units back into available inventory based on reservation ID.
    
    Args:
        reservation_id (int): ID of the Reservation record.
        
    Returns:
        Dict[str, Any]: JSON dict containing the operation status.
    """
    logger.info(f"[RELEASE_RESERVATION] Releasing reservation ID: {reservation_id}")
    try:
        db = DatabaseManager()
        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT inventory_id, reserved_units FROM Reservation WHERE id = ?", (reservation_id,))
            row = cursor.fetchone()
            
            if not row:
                logger.warning(f"[RELEASE_RESERVATION] Reservation {reservation_id} not found.")
                return {"status": "error", "message": "Reservation not found."}
                
            inventory_id = row['inventory_id']
            units = row['reserved_units']
            
            success = queries.release_reserved_units(inventory_id, units)
            if success:
                cursor.execute("UPDATE Reservation SET status = 'Released' WHERE id = ?", (reservation_id,))
                conn.commit()
                logger.info(f"[RELEASE_RESERVATION] Successfully released {units} units for reservation {reservation_id}.")
                return {"status": "success", "message": f"Successfully released {units} units for reservation {reservation_id}"}
            
            logger.error(f"[RELEASE_RESERVATION] Failed to release units in inventory {inventory_id}.")
            return {"status": "error", "message": "Failed to release units in inventory."}
    except Exception as e:
        logger.error(f"[RELEASE_RESERVATION] Error: {str(e)}", exc_info=True)
        return {"status": "error", "message": f"Database error occurred: {str(e)}"}

@registry.register()
def get_low_stock() -> Dict[str, Any]:
    """
    Generate a report of all inventory items that have fallen below their minimum threshold.
    
    Returns:
        Dict[str, Any]: JSON dict containing a list of low stock items.
    """
    logger.info("[LOW_STOCK_REPORT] Fetching low stock inventory.")
    try:
        low_stock = queries.get_low_stock_inventory()
        logger.info(f"[LOW_STOCK_REPORT] Found {len(low_stock)} inventory items below threshold.")
        return {"status": "success", "data": low_stock}
    except Exception as e:
        logger.error(f"[LOW_STOCK_REPORT] Error: {str(e)}", exc_info=True)
        return {"status": "error", "message": f"Database error occurred: {str(e)}"}

@registry.register()
def get_inventory_summary() -> Dict[str, Any]:
    """
    Get a high-level statistical summary of the entire blood inventory network.
    
    Returns:
        Dict[str, Any]: JSON dict containing global metrics (total facilities, units, etc).
    """
    logger.info("[INVENTORY_SUMMARY] Generating dashboard statistics.")
    try:
        stats = queries.get_dashboard_statistics()
        logger.info("[INVENTORY_SUMMARY] Statistics generated successfully.")
        return {"status": "success", "data": stats}
    except Exception as e:
        logger.error(f"[INVENTORY_SUMMARY] Error: {str(e)}", exc_info=True)
        return {"status": "error", "message": f"Database error occurred: {str(e)}"}
