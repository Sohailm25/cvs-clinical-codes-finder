# ABOUTME: Tests for checkpointing configuration and factory.
# ABOUTME: Validates checkpointer creation based on config.

import pytest
from unittest.mock import patch, MagicMock

from src.agent.checkpoint import get_checkpointer, get_checkpointer_sync


class TestGetCheckpointerSync:
    """Tests for synchronous checkpointer retrieval."""

    def test_returns_none_when_disabled(self):
        with patch("src.agent.checkpoint.config") as mock_config:
            mock_config.CHECKPOINT_ENABLED = False

            result = get_checkpointer_sync()

            assert result is None

    def test_returns_memory_saver_for_memory_backend(self):
        with patch("src.agent.checkpoint.config") as mock_config:
            mock_config.CHECKPOINT_ENABLED = True
            mock_config.CHECKPOINT_BACKEND = "memory"

            result = get_checkpointer_sync()

            assert result is not None
            # MemorySaver should be returned
            assert "MemorySaver" in type(result).__name__

    def test_returns_none_for_sqlite_backend(self):
        """SQLite requires async, so sync should return None."""
        with patch("src.agent.checkpoint.config") as mock_config:
            mock_config.CHECKPOINT_ENABLED = True
            mock_config.CHECKPOINT_BACKEND = "sqlite"

            result = get_checkpointer_sync()

            assert result is None

    def test_returns_none_for_postgres_backend(self):
        """Postgres requires async, so sync should return None."""
        with patch("src.agent.checkpoint.config") as mock_config:
            mock_config.CHECKPOINT_ENABLED = True
            mock_config.CHECKPOINT_BACKEND = "postgres"

            result = get_checkpointer_sync()

            assert result is None


class TestGetCheckpointer:
    """Tests for async checkpointer retrieval."""

    @pytest.mark.asyncio
    async def test_yields_none_when_disabled(self):
        with patch("src.agent.checkpoint.config") as mock_config:
            mock_config.CHECKPOINT_ENABLED = False

            async with get_checkpointer() as checkpointer:
                assert checkpointer is None

    @pytest.mark.asyncio
    async def test_yields_memory_saver_for_memory_backend(self):
        with patch("src.agent.checkpoint.config") as mock_config:
            mock_config.CHECKPOINT_ENABLED = True
            mock_config.CHECKPOINT_BACKEND = "memory"

            async with get_checkpointer() as checkpointer:
                assert checkpointer is not None
                assert "MemorySaver" in type(checkpointer).__name__

    @pytest.mark.asyncio
    async def test_falls_back_to_memory_for_unknown_backend(self):
        with patch("src.agent.checkpoint.config") as mock_config:
            mock_config.CHECKPOINT_ENABLED = True
            mock_config.CHECKPOINT_BACKEND = "unknown_backend"

            async with get_checkpointer() as checkpointer:
                assert checkpointer is not None
                assert "MemorySaver" in type(checkpointer).__name__

    @pytest.mark.asyncio
    async def test_postgres_without_uri_falls_back_to_memory(self):
        with patch("src.agent.checkpoint.config") as mock_config:
            mock_config.CHECKPOINT_ENABLED = True
            mock_config.CHECKPOINT_BACKEND = "postgres"
            mock_config.POSTGRES_URI = ""

            async with get_checkpointer() as checkpointer:
                assert checkpointer is not None
                assert "MemorySaver" in type(checkpointer).__name__


class TestCheckpointerWithGraph:
    """Integration tests for checkpointing with the agent graph."""

    @pytest.mark.asyncio
    async def test_graph_compiles_with_memory_saver(self):
        from langgraph.checkpoint.memory import MemorySaver
        from src.agent.graph import compile_graph

        checkpointer = MemorySaver()
        app = compile_graph(checkpointer=checkpointer)

        assert app is not None

    @pytest.mark.asyncio
    async def test_streaming_includes_thread_id(self):
        from src.agent.graph import run_agent_streaming

        events = []
        async for event in run_agent_streaming("diabetes", thread_id="test-thread"):
            events.append(event)
            break  # Just check first event

        assert len(events) > 0
        assert events[0]["thread_id"] == "test-thread"

    @pytest.mark.asyncio
    async def test_streaming_generates_thread_id_if_not_provided(self):
        from src.agent.graph import run_agent_streaming

        events = []
        async for event in run_agent_streaming("diabetes"):
            events.append(event)
            break  # Just check first event

        assert len(events) > 0
        assert "thread_id" in events[0]
        # Should be a UUID-like string
        assert len(events[0]["thread_id"]) == 36  # UUID format
