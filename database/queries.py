"""
Database Queries for BloodLink AI.
Contains all business logic queries for the application.
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta
from database.database import DatabaseManager
from utils.logger import logger

class BloodQueries:
    def __init__(self):
        self.db = DatabaseManager()

    def _execute_read(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Read query failed: {e}\nQuery: {query}\nParams: {params}")
            return []

    def _execute_write(self, query: str, params: tuple = ()) -> int:
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Write query failed: {e}\nQuery: {query}\nParams: {params}")
            raise

    def get_all_healthcare_facilities(self) -> List[Dict[str, Any]]:
        query = "SELECT * FROM HealthcareFacility"
        return self._execute_read(query)

    def get_inventory_by_blood_group(self, blood_group: str) -> List[Dict[str, Any]]:
        query = """
            SELECT bi.*, hf.name as facility_name 
            FROM BloodInventory bi
            JOIN HealthcareFacility hf ON bi.facility_id = hf.id
            WHERE bi.blood_group = ?
        """
        return self._execute_read(query, (blood_group,))

    def get_inventory_by_facility(self, facility_id: int) -> List[Dict[str, Any]]:
        query = "SELECT * FROM BloodInventory WHERE facility_id = ?"
        return self._execute_read(query, (facility_id,))

    def get_nearest_available_inventory(self, blood_group: str, component_type: str, latitude: float, longitude: float, required_units: int) -> List[Dict[str, Any]]:
        # Using Pythagorean approximation for distance sorting in SQLite
        query = """
            SELECT bi.*, hf.name, hf.latitude, hf.longitude,
                   ((hf.latitude - ?) * (hf.latitude - ?) + (hf.longitude - ?) * (hf.longitude - ?)) as distance_sq
            FROM BloodInventory bi
            JOIN HealthcareFacility hf ON bi.facility_id = hf.id
            WHERE bi.blood_group = ? AND bi.component_type = ? AND bi.units_available >= ?
            ORDER BY distance_sq ASC
        """
        return self._execute_read(query, (latitude, latitude, longitude, longitude, blood_group, component_type, required_units))

    def get_low_stock_inventory(self) -> List[Dict[str, Any]]:
        query = """
            SELECT bi.*, hf.name as facility_name 
            FROM BloodInventory bi
            JOIN HealthcareFacility hf ON bi.facility_id = hf.id
            WHERE bi.units_available <= bi.minimum_threshold
        """
        return self._execute_read(query)

    def reserve_units(self, inventory_id: int, units: int) -> bool:
        query = """
            UPDATE BloodInventory 
            SET units_available = units_available - ?,
                reserved_units = reserved_units + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND units_available >= ?
        """
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (units, units, inventory_id, units))
                if cursor.rowcount > 0:
                    conn.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to reserve units: {e}")
            return False

    def release_reserved_units(self, inventory_id: int, units: int) -> bool:
        query = """
            UPDATE BloodInventory 
            SET units_available = units_available + ?,
                reserved_units = reserved_units - ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND reserved_units >= ?
        """
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (units, units, inventory_id, units))
                if cursor.rowcount > 0:
                    conn.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to release reserved units: {e}")
            return False

    def update_inventory(self, inventory_id: int, new_units: int) -> bool:
        query = """
            UPDATE BloodInventory 
            SET units_available = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        try:
            self._execute_write(query, (new_units, inventory_id))
            return True
        except Exception:
            return False

    def create_blood_request(self, patient_id: int, requesting_facility_id: int, blood_group: str, component_type: str, requested_units: int, requested_priority: str, ai_priority: int = None, explanation: str = None) -> int:
        query = """
            INSERT INTO BloodRequest 
            (patient_id, requesting_facility_id, blood_group, component_type, requested_units, requested_priority, ai_priority, explanation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        return self._execute_write(query, (patient_id, requesting_facility_id, blood_group, component_type, requested_units, requested_priority, ai_priority, explanation))

    def get_pending_requests(self) -> List[Dict[str, Any]]:
        query = "SELECT * FROM BloodRequest WHERE status = 'Pending' ORDER BY request_date ASC"
        return self._execute_read(query)

    def update_request_status(self, request_id: int, status: str) -> bool:
        query = "UPDATE BloodRequest SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        try:
            self._execute_write(query, (status, request_id))
            return True
        except Exception:
            return False

    def get_patient(self, patient_id: int) -> Dict[str, Any]:
        query = "SELECT * FROM Patient WHERE id = ?"
        result = self._execute_read(query, (patient_id,))
        return result[0] if result else {}

    def get_donor(self, donor_id: int) -> Dict[str, Any]:
        query = "SELECT * FROM Donor WHERE id = ?"
        result = self._execute_read(query, (donor_id,))
        return result[0] if result else {}

    def get_all_eligible_donors(self) -> List[Dict[str, Any]]:
        query = """
            SELECT * FROM Donor 
            WHERE availability_status = 'Available' 
            AND (eligible_after IS NULL OR eligible_after <= date('now'))
        """
        return self._execute_read(query)

    def get_eligible_donors_by_blood_group(self, blood_group: str) -> List[Dict[str, Any]]:
        query = """
            SELECT * FROM Donor 
            WHERE availability_status = 'Available' 
            AND blood_group = ? 
            AND (eligible_after IS NULL OR eligible_after <= date('now'))
        """
        return self._execute_read(query, (blood_group,))

    def get_donors_due_for_next_donation(self) -> List[Dict[str, Any]]:
        query = """
            SELECT * FROM Donor 
            WHERE availability_status = 'Available' 
            AND (eligible_after IS NOT NULL AND eligible_after <= date('now'))
        """
        return self._execute_read(query)

    def get_recent_donations(self, days: int) -> List[Dict[str, Any]]:
        date_threshold = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        query = """
            SELECT dh.*, d.first_name, d.last_name, hf.name as facility_name
            FROM DonationHistory dh
            JOIN Donor d ON dh.donor_id = d.id
            JOIN HealthcareFacility hf ON dh.facility_id = hf.id
            WHERE dh.donation_date >= ?
            ORDER BY dh.donation_date DESC
        """
        return self._execute_read(query, (date_threshold,))

    def create_notification(self, donor_id: int, facility_id: int, notification_type: str, message: str, recipient_type: str, delivery_channel: str) -> int:
        query = """
            INSERT INTO Notification 
            (donor_id, facility_id, notification_type, message, recipient_type, delivery_channel)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        return self._execute_write(query, (donor_id, facility_id, notification_type, message, recipient_type, delivery_channel))

    def save_agent_decision(self, agent_name: str, decision_type: str, context: str, reasoning: str) -> int:
        query = """
            INSERT INTO AgentDecisionLog 
            (agent_name, decision_type, context, reasoning)
            VALUES (?, ?, ?, ?)
        """
        return self._execute_write(query, (agent_name, decision_type, context, reasoning))

    def get_dashboard_statistics(self) -> Dict[str, Any]:
        stats = {}
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) as count FROM HealthcareFacility")
                stats['total_facilities'] = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(*) as count FROM Donor WHERE availability_status = 'Available'")
                stats['available_donors'] = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(*) as count FROM BloodRequest WHERE status = 'Pending'")
                stats['pending_requests'] = cursor.fetchone()['count']
                
                cursor.execute("SELECT SUM(units_available) as count FROM BloodInventory")
                stats['total_units_available'] = cursor.fetchone()['count'] or 0
                
        except Exception as e:
            logger.error(f"Failed to get dashboard statistics: {e}")
            
        return stats
