"""
Database Verification Script.
Checks if all required tables exist in the SQLite database.
"""

from database.database import DatabaseManager
from utils.logger import logger

def verify_db():
    expected_tables = {
        "HealthcareFacility",
        "Donor",
        "Patient",
        "BloodInventory",
        "DonationHistory",
        "BloodRequest",
        "Reservation",
        "Notification",
        "InventoryAudit",
        "EmergencyEvent",
        "DonorNotificationResponse",
        "AgentDecisionLog"
    }

    db = DatabaseManager()
    
    try:
        logger.info("Connecting to database for verification...")
        conn = db.connect()
        cursor = conn.cursor()
        
        # Query to get all table names in SQLite
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        rows = cursor.fetchall()
        
        actual_tables = {row['name'] for row in rows}
        
        logger.info("--- Tables found in Database ---")
        for table in sorted(actual_tables):
            logger.info(f"- {table}")
            
        logger.info(f"Total number of tables found: {len(actual_tables)}")
        
        missing_tables = expected_tables - actual_tables
        
        if missing_tables:
            logger.error(f"Verification failed. Missing expected tables: {', '.join(missing_tables)}")
        else:
            logger.info("Database verification successful.")
            
    except Exception as e:
        logger.error(f"An error occurred during verification: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify_db()
