"""
Database Initialization Script.
Reads schema.sql and creates all tables in the SQLite database.
"""

import os
from database.database import DatabaseManager
from utils.logger import logger

def init_db() -> None:
    """Initializes the database using schema.sql."""
    # Determine path to schema.sql relative to this script
    base_dir = os.path.dirname(os.path.abspath(__file__))
    schema_path = os.path.join(base_dir, 'schema.sql')

    if not os.path.exists(schema_path):
        logger.error(f"Schema file not found at {schema_path}")
        return

    logger.info("Reading schema.sql...")
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()

    db = DatabaseManager()
    
    try:
        logger.info("Connecting to database...")
        conn = db.connect()
        
        # Explicitly enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON;")
        logger.info("Foreign keys enabled.")
        
        logger.info("Executing schema to create tables...")
        # executescript allows executing multiple SQL statements separated by semicolons
        conn.executescript(schema_sql)
        
        logger.info("Database initialization successful! All tables created.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
