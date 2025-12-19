# ABOUTME: Tests for in-memory cache with TTL.
# ABOUTME: Validates LRU eviction, expiration, and API response caching.

import asyncio

import pytest

from src.services.cache import InMemoryCache, APIResponseCache


class TestInMemoryCache:
    """Tests for in-memory LRU cache."""

    @pytest.mark.asyncio
    async def test_get_set_basic(self):
        """Basic get/set should work."""
        cache = InMemoryCache()
        await cache.set("key1", {"data": 123}, ttl=60)
        result = await cache.get("key1")
        assert result == {"data": 123}

    @pytest.mark.asyncio
    async def test_get_missing_key_returns_none(self):
        """Missing key should return None."""
        cache = InMemoryCache()
        result = await cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_ttl_expiration(self):
        """Expired entries should return None."""
        cache = InMemoryCache()
        await cache.set("key1", "value", ttl=0)
        await asyncio.sleep(0.01)
        result = await cache.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_lru_eviction(self):
        """Oldest entry should be evicted when over capacity."""
        cache = InMemoryCache(max_size=2)
        await cache.set("key1", "v1", ttl=60)
        await cache.set("key2", "v2", ttl=60)
        await cache.set("key3", "v3", ttl=60)

        # key1 should be evicted
        assert await cache.get("key1") is None
        assert await cache.get("key2") == "v2"
        assert await cache.get("key3") == "v3"

    @pytest.mark.asyncio
    async def test_lru_access_updates_order(self):
        """Accessing an entry should move it to end (prevent eviction)."""
        cache = InMemoryCache(max_size=2)
        await cache.set("key1", "v1", ttl=60)
        await cache.set("key2", "v2", ttl=60)

        # Access key1 to make it recent
        await cache.get("key1")

        # Add key3, should evict key2 (not key1)
        await cache.set("key3", "v3", ttl=60)

        assert await cache.get("key1") == "v1"
        assert await cache.get("key2") is None
        assert await cache.get("key3") == "v3"

    @pytest.mark.asyncio
    async def test_delete(self):
        """Delete should remove entry."""
        cache = InMemoryCache()
        await cache.set("key1", "value", ttl=60)
        await cache.delete("key1")
        assert await cache.get("key1") is None

    @pytest.mark.asyncio
    async def test_clear(self):
        """Clear should remove all entries."""
        cache = InMemoryCache()
        await cache.set("key1", "v1", ttl=60)
        await cache.set("key2", "v2", ttl=60)
        await cache.clear()
        assert cache.size() == 0

    @pytest.mark.asyncio
    async def test_size(self):
        """Size should return current entry count."""
        cache = InMemoryCache()
        assert cache.size() == 0
        await cache.set("key1", "v1", ttl=60)
        assert cache.size() == 1
        await cache.set("key2", "v2", ttl=60)
        assert cache.size() == 2


class TestAPIResponseCache:
    """Tests for API response cache wrapper."""

    @pytest.mark.asyncio
    async def test_cache_api_response(self):
        """Should cache and retrieve API responses."""
        cache = APIResponseCache(default_ttl=60)
        params = {"terms": "diabetes", "maxList": 10}
        response = [5, ["E11.9"], {}, [["E11.9", "Diabetes"]]]

        await cache.set("icd10cm", params, response)
        result = await cache.get("icd10cm", params)

        assert result == response

    @pytest.mark.asyncio
    async def test_different_params_different_keys(self):
        """Different params should produce different cache keys."""
        cache = APIResponseCache(default_ttl=60)
        params1 = {"terms": "diabetes", "maxList": 10}
        params2 = {"terms": "hypertension", "maxList": 10}

        await cache.set("icd10cm", params1, ["response1"])
        await cache.set("icd10cm", params2, ["response2"])

        assert await cache.get("icd10cm", params1) == ["response1"]
        assert await cache.get("icd10cm", params2) == ["response2"]

    @pytest.mark.asyncio
    async def test_stats_tracking(self):
        """Should track hit/miss statistics."""
        cache = APIResponseCache(default_ttl=60)
        params = {"terms": "test"}

        # Miss
        await cache.get("icd10cm", params)
        assert cache.stats["misses"] == 1
        assert cache.stats["hits"] == 0

        # Set and hit
        await cache.set("icd10cm", params, ["data"])
        await cache.get("icd10cm", params)
        assert cache.stats["hits"] == 1
        assert cache.stats["misses"] == 1

    @pytest.mark.asyncio
    async def test_custom_ttl(self):
        """Should respect custom TTL for specific entries."""
        backend = InMemoryCache()
        cache = APIResponseCache(backend=backend, default_ttl=3600)
        params = {"terms": "test"}

        # Set with immediate expiration
        await cache.set("icd10cm", params, ["data"], ttl=0)
        await asyncio.sleep(0.01)

        result = await cache.get("icd10cm", params)
        assert result is None
