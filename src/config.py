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

    # HTTP pooling settings
    HTTP_MAX_CONNECTIONS: int = int(os.getenv("HTTP_MAX_CONNECTIONS", "20"))
    HTTP_MAX_KEEPALIVE: int = int(os.getenv("HTTP_MAX_KEEPALIVE", "10"))

    # Cache settings
    CACHE_ENABLED: bool = os.getenv("CACHE_ENABLED", "true").lower() == "true"
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "3600"))
    CACHE_MAX_SIZE: int = int(os.getenv("CACHE_MAX_SIZE", "1000"))

    # Semantic reranking settings
    SEMANTIC_RERANK_ENABLED: bool = (
        os.getenv("SEMANTIC_RERANK_ENABLED", "false").lower() == "true"
    )
    RERANKER_MODEL: str = os.getenv(
        "RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
    )
    RERANKER_WEIGHT_SEMANTIC: float = float(
        os.getenv("RERANKER_WEIGHT_SEMANTIC", "0.6")
    )
    RERANKER_WEIGHT_LEXICAL: float = float(
        os.getenv("RERANKER_WEIGHT_LEXICAL", "0.4")
    )

    # Query expansion settings
    EXPANSION_ENABLED: bool = os.getenv("EXPANSION_ENABLED", "true").lower() == "true"
    EXPANSION_MODEL: str = os.getenv("EXPANSION_MODEL", "gpt-4o-mini")
    EXPANSION_CACHE_TTL: int = int(os.getenv("EXPANSION_CACHE_TTL", "86400"))

    # Checkpointing settings
    CHECKPOINT_ENABLED: bool = (
        os.getenv("CHECKPOINT_ENABLED", "false").lower() == "true"
    )
    CHECKPOINT_BACKEND: str = os.getenv("CHECKPOINT_BACKEND", "memory")
    CHECKPOINT_SQLITE_PATH: str = os.getenv(
        "CHECKPOINT_SQLITE_PATH", ".clinical_codes_checkpoints.db"
    )
    POSTGRES_URI: str = os.getenv("POSTGRES_URI", "")

    @classmethod
    def validate(cls) -> None:
        """Validate required configuration."""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable is required")


config = Config()
