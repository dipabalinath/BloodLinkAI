import pytest
import sqlite3
import os
from unittest.mock import patch
from mcp_server.tools.inventory_tools import release_reservation
from database.database import DatabaseManager
from database.queries import queries

@pytest.fixture
def test_db():
    # Setup in-memory DB for tests
    db_path = ":memory:"
    manager = DatabaseManager()
    manager.db_path = db_path
    
    # Init schema
    schema_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'schema.sql')
    with open(schema_path, 'r') as f:
        schema = f.read()
    
    with manager.connect() as conn:
        conn.executescript(schema)
        
        # Insert base data
        cursor = conn.cursor()
        cursor.execute("INSERT INTO HealthcareFacility (name, facility_type, city) VALUES ('Test Hosp', 'Hospital', 'NY')")
        f_id = cursor.lastrowid
        
        cursor.execute("INSERT INTO Patient (first_name, last_name, blood_group, facility_id) VALUES ('John', 'Doe', 'A+', ?)", (f_id,))
        p_id = cursor.lastrowid
        
        cursor.execute("INSERT INTO BloodRequest (patient_id, requesting_facility_id, blood_group, component_type, requested_units, requested_priority) VALUES (?, ?, 'A+', 'Packed RBC', 2, 'TIER_2_URGENT')", (p_id, f_id))
        r_id = cursor.lastrowid
        
        cursor.execute("INSERT INTO BloodInventory (facility_id, blood_group, component_type, units_available, reserved_units, collection_date, expiry_date) VALUES (?, 'A+', 'Packed RBC', 10, 2, '2026-07-01', '2026-07-20')", (f_id,))
        inv_id = cursor.lastrowid
        
        # Add 2 reservations for this request
        cursor.execute("INSERT INTO Reservation (request_id, inventory_id, reserved_units, status) VALUES (?, ?, 1, 'Active')", (r_id, inv_id))
        cursor.execute("INSERT INTO Reservation (request_id, inventory_id, reserved_units, status) VALUES (?, ?, 1, 'Active')", (r_id, inv_id))
        
        conn.commit()
    
    yield manager

def test_release_reservation(test_db):
    with patch('mcp_server.tools.inventory_tools.DatabaseManager', return_value=test_db):
        with patch('database.queries.DatabaseManager', return_value=test_db):
            # There is 1 request with ID 1 containing 2 reservations (total 2 units).
            request_id = 1
            
            # Initial inventory check
            with test_db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT units_available, reserved_units FROM BloodInventory WHERE id = 1")
                inv = cursor.fetchone()
                assert inv['units_available'] == 10
                assert inv['reserved_units'] == 2
            
            # Call MCP tool
            result = release_reservation(request_id)
            
            # Assertions
            assert result['status'] == 'success'
            assert result['released_count'] == 2
            assert result['units_restored'] == 2
            
            # Inventory validation
            with test_db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT units_available, reserved_units FROM BloodInventory WHERE id = 1")
                inv = cursor.fetchone()
                assert inv['units_available'] == 12
                assert inv['reserved_units'] == 0
                
                # Check status
                cursor.execute("SELECT status FROM Reservation WHERE request_id = 1")
                for row in cursor.fetchall():
                    assert row['status'] == 'Released'

def test_release_reservation_not_found(test_db):
    with patch('mcp_server.tools.inventory_tools.DatabaseManager', return_value=test_db):
        # Invalid request ID
        result = release_reservation(999)
        assert result['status'] == 'error'
        assert 'No active reservations found' in result['message']
