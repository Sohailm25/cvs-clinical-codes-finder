# ABOUTME: Checkpointing configuration for LangGraph state persistence.
# ABOUTME: Provides tiered fallback: MemorySaver -> SqliteSaver -> PostgresSaver.

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Any

from src.config import config

logger = logging.getLogger(__name__)


@asynccontextmanager
async def get_checkpointer() -> AsyncGenerator[Any, None]:
    """
    Get the appropriate checkpointer based on configuration.

    Tiered fallback:
    1. If CHECKPOINT_ENABLED is False, yield None (no checkpointing)
    2. CHECKPOINT_BACKEND="memory" -> MemorySaver (default)
    3. CHECKPOINT_BACKEND="sqlite" -> SqliteSaver
    4. CHECKPOINT_BACKEND="postgres" -> AsyncPostgresSaver (requires POSTGRES_URI)

    Yields:
        Checkpointer instance or None if disabled.
    """
    if not config.CHECKPOINT_ENABLED:
        logger.debug("Checkpointing disabled")
        yield None
        return

    backend = config.CHECKPOINT_BACKEND.lower()
    checkpointer = None

    try:
        if backend == "memory":
            from langgraph.checkpoint.memory import MemorySaver
            checkpointer = MemorySaver()
            logger.info("Using MemorySaver checkpointer")

        elif backend == "sqlite":
            from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
            sqlite_path = config.CHECKPOINT_SQLITE_PATH
            logger.info(f"Using SqliteSaver checkpointer: {sqlite_path}")
            async with AsyncSqliteSaver.from_conn_string(sqlite_path) as saver:
                yield saver
                return

        elif backend == "postgres":
            if not config.POSTGRES_URI:
                logger.warning("POSTGRES_URI not set, falling back to MemorySaver")
                from langgraph.checkpoint.memory import MemorySaver
                checkpointer = MemorySaver()
            else:
                try:
                    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
                    logger.info("Using PostgresSaver checkpointer")
                    async with AsyncPostgresSaver.from_conn_string(config.POSTGRES_URI) as saver:
                        yield saver
                        return
                except ImportError:
                    logger.warning("langgraph-checkpoint-postgres not installed, falling back to MemorySaver")
                    from langgraph.checkpoint.memory import MemorySaver
                    checkpointer = MemorySaver()
        else:
            logger.warning(f"Unknown backend '{backend}', using MemorySaver")
            from langgraph.checkpoint.memory import MemorySaver
            checkpointer = MemorySaver()

        yield checkpointer

    finally:
        # Clean up if needed (MemorySaver doesn't need cleanup)
        pass


def get_checkpointer_sync() -> Any:
    """
    Synchronous version for simple use cases.

    Returns MemorySaver or None if disabled.
    """
    if not config.CHECKPOINT_ENABLED:
        return None

    backend = config.CHECKPOINT_BACKEND.lower()

    if backend == "memory":
        from langgraph.checkpoint.memory import MemorySaver
        return MemorySaver()

    # For other backends, return None and require async usage
    logger.warning(f"Backend '{backend}' requires async usage, returning None")
    return None
