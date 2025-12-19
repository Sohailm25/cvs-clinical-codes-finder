# ABOUTME: Thread-safe singleton for loading cross-encoder models.
# ABOUTME: Lazy loads models on first use to avoid startup delay.

import asyncio
import logging
from typing import ClassVar

from src.config import config

logger = logging.getLogger(__name__)


class ModelCache:
    """Singleton manager for cross-encoder models."""

    _instance: ClassVar["ModelCache | None"] = None
    _lock: ClassVar[asyncio.Lock] = asyncio.Lock()

    def __init__(self):
        self._model = None
        self._model_name: str | None = None
        self._load_lock = asyncio.Lock()

    @classmethod
    async def get_instance(cls) -> "ModelCache":
        """Get or create the singleton instance."""
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def get_instance_sync(cls) -> "ModelCache":
        """Get or create the singleton instance (sync version)."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def get_model(self, model_name: str | None = None):
        """
        Get the cross-encoder model, loading if necessary.

        Args:
            model_name: Model to load. If None, uses config.RERANKER_MODEL.

        Returns:
            CrossEncoder model instance.
        """
        target_model = model_name or config.RERANKER_MODEL

        # Check if already loaded
        if self._model is not None and self._model_name == target_model:
            return self._model

        async with self._load_lock:
            # Double-check after acquiring lock
            if self._model is not None and self._model_name == target_model:
                return self._model

            logger.info(f"Loading cross-encoder model: {target_model}")

            # Load in thread pool to avoid blocking event loop
            loop = asyncio.get_event_loop()
            self._model = await loop.run_in_executor(
                None, self._load_model_sync, target_model
            )
            self._model_name = target_model

            logger.info(f"Model loaded: {target_model}")
            return self._model

    def _load_model_sync(self, model_name: str):
        """Synchronously load the model (called in thread pool)."""
        try:
            from sentence_transformers import CrossEncoder

            return CrossEncoder(model_name)
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            raise

    def is_loaded(self) -> bool:
        """Check if a model is currently loaded."""
        return self._model is not None

    @property
    def current_model_name(self) -> str | None:
        """Get the name of the currently loaded model."""
        return self._model_name

    def clear(self) -> None:
        """Clear the cached model (for testing)."""
        self._model = None
        self._model_name = None

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (for testing)."""
        if cls._instance:
            cls._instance.clear()
        cls._instance = None
