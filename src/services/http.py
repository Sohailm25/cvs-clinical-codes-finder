# ABOUTME: Managed HTTP client with connection pooling.
# ABOUTME: Provides singleton client for Clinical Tables API requests.

import asyncio
import logging
from typing import ClassVar

import httpx

from src.config import config

logger = logging.getLogger(__name__)


class HTTPClientManager:
    """Singleton manager for HTTP client with connection pooling."""

    _instance: ClassVar["HTTPClientManager | None"] = None
    _lock: ClassVar[asyncio.Lock] = asyncio.Lock()

    def __init__(
        self,
        timeout: float | None = None,
        max_connections: int | None = None,
        max_keepalive_connections: int | None = None,
    ):
        self._timeout = timeout or getattr(config, "API_TIMEOUT", 5.0)
        self._max_connections = max_connections or getattr(
            config, "HTTP_MAX_CONNECTIONS", 20
        )
        self._max_keepalive = max_keepalive_connections or getattr(
            config, "HTTP_MAX_KEEPALIVE", 10
        )
        self._client: httpx.AsyncClient | None = None
        self._client_lock = asyncio.Lock()

    @classmethod
    async def get_instance(cls) -> "HTTPClientManager":
        """Get or create the singleton instance."""
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def get_instance_sync(cls) -> "HTTPClientManager":
        """Get or create the singleton instance (sync version for init)."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @staticmethod
    def _check_http2_available() -> bool:
        """Check if HTTP/2 support is available."""
        try:
            import h2  # noqa: F401
            return True
        except ImportError:
            return False

    async def get_client(self) -> httpx.AsyncClient:
        """Get or create the pooled HTTP client."""
        if self._client is None or self._client.is_closed:
            async with self._client_lock:
                if self._client is None or self._client.is_closed:
                    logger.debug(
                        f"Creating HTTP client pool: max_connections={self._max_connections}"
                    )
                    # Only enable HTTP/2 if h2 is installed
                    http2_enabled = self._check_http2_available()
                    self._client = httpx.AsyncClient(
                        timeout=httpx.Timeout(self._timeout),
                        limits=httpx.Limits(
                            max_connections=self._max_connections,
                            max_keepalive_connections=self._max_keepalive,
                        ),
                        http2=http2_enabled,
                    )
        return self._client

    async def close(self) -> None:
        """Close the client and release connections."""
        if self._client and not self._client.is_closed:
            logger.debug("Closing HTTP client pool")
            await self._client.aclose()
            self._client = None

    @classmethod
    async def shutdown(cls) -> None:
        """Shutdown hook for graceful cleanup."""
        if cls._instance:
            await cls._instance.close()
            cls._instance = None

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (for testing)."""
        cls._instance = None
