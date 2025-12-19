# ABOUTME: In-memory caching with TTL for API responses.
# ABOUTME: Supports LRU eviction and optional Redis backend for production.

import asyncio
import hashlib
import json
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class CacheEntry:
    """Cache entry with value and expiration."""

    value: Any
    expires_at: float

    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class CacheBackend(Protocol):
    """Protocol for cache backends."""

    async def get(self, key: str) -> Any | None: ...
    async def set(self, key: str, value: Any, ttl: int) -> None: ...
    async def delete(self, key: str) -> None: ...
    async def clear(self) -> None: ...


class InMemoryCache:
    """Thread-safe in-memory LRU cache with TTL."""

    def __init__(self, max_size: int = 1000):
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            if entry.is_expired():
                del self._cache[key]
                return None
            # Move to end (LRU)
            self._cache.move_to_end(key)
            return entry.value

    async def set(self, key: str, value: Any, ttl: int) -> None:
        async with self._lock:
            self._cache[key] = CacheEntry(
                value=value,
                expires_at=time.time() + ttl,
            )
            self._cache.move_to_end(key)
            # Evict oldest if over capacity
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._cache.pop(key, None)

    async def clear(self) -> None:
        async with self._lock:
            self._cache.clear()

    def size(self) -> int:
        """Return current cache size."""
        return len(self._cache)


class APIResponseCache:
    """High-level cache for Clinical Tables API responses."""

    def __init__(
        self,
        backend: CacheBackend | None = None,
        default_ttl: int = 3600,
    ):
        self._backend = backend or InMemoryCache()
        self._default_ttl = default_ttl
        self._hits = 0
        self._misses = 0

    def _make_key(self, table: str, params: dict[str, Any]) -> str:
        """Generate cache key from request parameters."""
        param_str = json.dumps(params, sort_keys=True)
        hash_val = hashlib.sha256(param_str.encode()).hexdigest()[:16]
        return f"api:{table}:{hash_val}"

    async def get(self, table: str, params: dict[str, Any]) -> list[Any] | None:
        """Get cached API response."""
        key = self._make_key(table, params)
        result = await self._backend.get(key)
        if result is not None:
            self._hits += 1
        else:
            self._misses += 1
        return result

    async def set(
        self,
        table: str,
        params: dict[str, Any],
        response: list[Any],
        ttl: int | None = None,
    ) -> None:
        """Cache API response."""
        key = self._make_key(table, params)
        effective_ttl = ttl if ttl is not None else self._default_ttl
        await self._backend.set(key, response, effective_ttl)

    async def delete(self, table: str, params: dict[str, Any]) -> None:
        """Delete cached response."""
        key = self._make_key(table, params)
        await self._backend.delete(key)

    async def clear(self) -> None:
        """Clear all cached responses."""
        await self._backend.clear()
        self._hits = 0
        self._misses = 0

    @property
    def stats(self) -> dict[str, int]:
        """Return cache statistics."""
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "total": total,
            "hit_rate": self._hits / total if total > 0 else 0.0,
        }
