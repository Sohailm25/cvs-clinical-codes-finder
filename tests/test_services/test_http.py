# ABOUTME: Tests for HTTP client manager with connection pooling.
# ABOUTME: Validates singleton behavior, connection reuse, and cleanup.

import pytest

from src.services.http import HTTPClientManager


class TestHTTPClientManager:
    """Tests for HTTP client manager."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before and after each test."""
        HTTPClientManager.reset()
        yield
        HTTPClientManager.reset()

    @pytest.mark.asyncio
    async def test_singleton_instance(self):
        """Should return same instance on multiple calls."""
        instance1 = await HTTPClientManager.get_instance()
        instance2 = await HTTPClientManager.get_instance()
        assert instance1 is instance2

    @pytest.mark.asyncio
    async def test_get_client_returns_client(self):
        """Should return httpx.AsyncClient."""
        manager = await HTTPClientManager.get_instance()
        client = await manager.get_client()

        assert client is not None
        assert not client.is_closed

    @pytest.mark.asyncio
    async def test_client_reuse(self):
        """Should return same client on multiple calls."""
        manager = await HTTPClientManager.get_instance()
        client1 = await manager.get_client()
        client2 = await manager.get_client()

        assert client1 is client2

    @pytest.mark.asyncio
    async def test_close_closes_client(self):
        """Close should close the underlying client."""
        manager = await HTTPClientManager.get_instance()
        client = await manager.get_client()

        await manager.close()

        assert client.is_closed

    @pytest.mark.asyncio
    async def test_get_client_after_close_creates_new(self):
        """Should create new client after close."""
        manager = await HTTPClientManager.get_instance()
        client1 = await manager.get_client()
        await manager.close()

        client2 = await manager.get_client()

        assert client2 is not client1
        assert not client2.is_closed

    @pytest.mark.asyncio
    async def test_shutdown_clears_singleton(self):
        """Shutdown should clear the singleton instance."""
        await HTTPClientManager.get_instance()
        await HTTPClientManager.shutdown()

        assert HTTPClientManager._instance is None

    def test_sync_get_instance(self):
        """Sync version should work for initialization."""
        manager = HTTPClientManager.get_instance_sync()
        assert manager is not None
        assert HTTPClientManager._instance is manager
