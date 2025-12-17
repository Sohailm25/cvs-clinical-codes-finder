# ABOUTME: Configuration management for Clinical Codes Finder.
# ABOUTME: Loads settings from environment variables with sensible defaults.

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration."""

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")

    # Agent settings
    MAX_ITERATIONS: int = int(os.getenv("MAX_ITERATIONS", "3"))
    MAX_API_CALLS: int = int(os.getenv("MAX_API_CALLS", "12"))
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.3"))

    # API settings
    API_TIMEOUT: float = float(os.getenv("API_TIMEOUT", "5.0"))
    MAX_RESULTS_PER_SYSTEM: int = int(os.getenv("MAX_RESULTS_PER_SYSTEM", "10"))

    @classmethod
    def validate(cls) -> None:
        """Validate required configuration."""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable is required")


config = Config()
