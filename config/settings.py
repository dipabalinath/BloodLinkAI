"""
Settings module for BloodLink AI.
Loads and validates configuration from environment variables.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """
    Configuration settings for BloodLink AI.
    Provides validated access to environment variables.
    """
    
    # Core settings
    GOOGLE_API_KEY: str
    MODEL_NAME: str
    DATABASE_URL: str
    APP_NAME: str
    APP_ENV: str
    DEBUG: bool
    LOG_LEVEL: str
    USE_MOCK_AI: bool

    # Domain specific settings
    DEFAULT_SEARCH_RADIUS: int
    LOW_STOCK_THRESHOLD: int
    MIN_DONOR_AGE: int
    MAX_DONOR_AGE: int
    MIN_DONOR_WEIGHT: float
    DONATION_INTERVAL_DAYS: int

    def __init__(self) -> None:
        """Initializes settings, falling back to defaults where appropriate and validating required fields."""
        
        self.GOOGLE_API_KEY = self._get_required_env("GOOGLE_API_KEY")
        self.DATABASE_URL = self._get_required_env("DATABASE_URL")
        self.MODEL_NAME = os.getenv("MODEL_NAME", "gemini-3.5-flash")
        
        self.APP_NAME = os.getenv("APP_NAME", "BloodLinkAI")
        self.APP_ENV = os.getenv("APP_ENV", "development")
        self.DEBUG = self._get_bool_env("DEBUG", True)
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        self.USE_MOCK_AI = self._get_bool_env("USE_MOCK_AI", True)
        
        self.DEFAULT_SEARCH_RADIUS = self._get_int_env("DEFAULT_SEARCH_RADIUS", 20)
        self.LOW_STOCK_THRESHOLD = self._get_int_env("LOW_STOCK_THRESHOLD", 10)
        self.MIN_DONOR_AGE = self._get_int_env("MIN_DONOR_AGE", 18)
        self.MAX_DONOR_AGE = self._get_int_env("MAX_DONOR_AGE", 65)
        self.MIN_DONOR_WEIGHT = self._get_float_env("MIN_DONOR_WEIGHT", 50.0)
        self.DONATION_INTERVAL_DAYS = self._get_int_env("DONATION_INTERVAL_DAYS", 90)

    def _get_required_env(self, key: str) -> str:
        """Retrieves an environment variable and raises ValueError if not set."""
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Missing required environment variable: {key}")
        return value

    def _get_int_env(self, key: str, default: int) -> int:
        """Retrieves an environment variable as an integer."""
        value = os.getenv(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            raise ValueError(f"Environment variable {key} must be an integer, got: {value}")

    def _get_float_env(self, key: str, default: float) -> float:
        """Retrieves an environment variable as a float."""
        value = os.getenv(key)
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            raise ValueError(f"Environment variable {key} must be a float, got: {value}")
            
    def _get_bool_env(self, key: str, default: bool) -> bool:
        """Retrieves an environment variable as a boolean."""
        value = os.getenv(key)
        if value is None:
            return default
        return str(value).lower() in ("true", "1", "yes", "t", "y")


# Expose a singleton instance of Settings
settings = Settings()
