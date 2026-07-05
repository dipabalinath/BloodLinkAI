"""
Main entry point for BloodLink AI.
Initializes core components like settings, logger, and the database.
"""

import sys

# Load components
from config.settings import settings
from utils.logger import logger
from database.database import DatabaseManager


def print_banner() -> None:
    """Prints the startup banner for the application."""
    banner = f"""
    =================================================
    {settings.APP_NAME}
    AI Powered Blood Supply Management
    
    Environment: {settings.APP_ENV}
    Debug Mode: {'ON' if settings.DEBUG else 'OFF'}
    Log Level: {settings.LOG_LEVEL}
    =================================================
    """
    print(banner)


def main() -> None:
    """Main application execution flow."""
    print_banner()
    logger.info("Starting BloodLink AI initialization...")

    db = None
    try:
        # Initialize and connect to the database
        logger.info("Initializing DatabaseManager...")
        db = DatabaseManager()
        db.connect()
        logger.info("Database connected successfully.")

        # Core application logic will go here
        logger.info("System initialized. AI agents are currently disabled/pending implementation.")
        
        # Simulating main loop or process completion
        logger.info("Main execution flow finished successfully.")

    except Exception as e:
        # Gracefully handle any exceptions that bubble up
        logger.critical(f"A critical error occurred: {e}", exc_info=settings.DEBUG)
        sys.exit(1)
    finally:
        # Guarantee graceful shutdown of resources
        if db:
            logger.info("Cleaning up resources...")
            db.close()
        
        logger.info("BloodLink AI shutdown complete.")


if __name__ == "__main__":
    main()
