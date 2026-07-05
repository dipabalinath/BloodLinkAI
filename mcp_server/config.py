"""
Configuration for BloodLink MCP Server.
Loads environment variables from .env and provides server-wide constants.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Environment variables with defaults
HOST: str = os.environ.get("HOST", "127.0.0.1")
PORT: int = int(os.environ.get("PORT", 8001))
LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")

# Server constants
SERVER_NAME: str = "BloodLink MCP"
VERSION: str = "1.0"
AUTHOR: str = "BloodLink AI"
