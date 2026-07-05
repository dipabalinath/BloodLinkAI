"""
Logger module for BloodLink AI.
Sets up a singleton logger with console and file output.
"""

import logging
import os
from config.settings import settings

def _setup_logger() -> logging.Logger:
    """Configures and returns a singleton logger instance."""
    # Create the logger
    logger = logging.getLogger(settings.APP_NAME)
    
    # If handlers already exist, return the configured logger (singleton behavior)
    if logger.hasHandlers():
        return logger

    # Retrieve and set log level from settings (default to INFO if invalid)
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(log_level)

    # Create formatter with timestamp
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 1. Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. File Handler
    # Determine absolute path to the logs directory at the project root
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_dir = os.path.join(base_dir, 'logs')
    
    # Create logs directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    # Setup file handler
    file_path = os.path.join(log_dir, 'app.log')
    file_handler = logging.FileHandler(file_path, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Prevent logs from propagating to the root logger to avoid duplication
    logger.propagate = False

    return logger

# Expose a singleton logger instance
logger = _setup_logger()
