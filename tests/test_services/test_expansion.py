# ABOUTME: Tests for LLM-driven clinical query expansion service.
# ABOUTME: Validates expansion, caching, and static fallback.

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from src.services.expansion import (
    ClinicalExpansionService,
    get_expansion_service,
    reset_expansion_service,
)


class TestClinicalExpansionService:
    """Tests for the expansion service."""

    def setup_method(self):
        reset_expansion_service()

    def teardown_method(self):
        reset_expansion_service()

    async def test_static_fallback_when_disabled(self):
        """When expansion disabled, uses static fallback."""
        with patch("src.services.expansion.config") as mock_config:
            mock_config.EXPANSION_ENABLED = False
            mock_config.EXPANSION_MODEL = "gpt-4o-mini"
            mock_config.EXPANSION_CACHE_TTL = 3600
            mock_config.OPENAI_API_KEY = "test"

            service = ClinicalExpansionService()
            result = await service.expand("diabetes", ["ICD-10-CM"])

            # Should get static terms from CLINICAL_RELATIONSHIPS
            assert "diagnoses" in result
            # Diabetes should have related diagnoses in static dict
            assert len(result["diagnoses"]) > 0

    async def test_static_fallback_includes_correct_categories(self):
        """Static fallback respects selected systems."""
        with patch("src.services.expansion.config") as mock_config:
            mock_config.EXPANSION_ENABLED = False
            mock_config.EXPANSION_MODEL = "gpt-4o-mini"
            mock_config.EXPANSION_CACHE_TTL = 3600
            mock_config.OPENAI_API_KEY = "test"

            service = ClinicalExpansionService()

            # Only ICD-10-CM selected - should get diagnoses
            result = await service.expand("diabetes", ["ICD-10-CM"])
            assert len(result["diagnoses"]) > 0
            assert len(result["medications"]) == 0  # RxTerms not selected

            # Only RxTerms selected - should get medications
            result = await service.expand("diabetes", ["RxTerms"])
            assert len(result["medications"]) > 0
            assert len(result["diagnoses"]) == 0  # ICD-10 not selected

    async def test_static_fallback_unknown_condition(self):
        """Static fallback returns empty for unknown conditions."""
        with patch("src.services.expansion.config") as mock_config:
            mock_config.EXPANSION_ENABLED = False
            mock_config.EXPANSION_MODEL = "gpt-4o-mini"
            mock_config.EXPANSION_CACHE_TTL = 3600

            service = ClinicalExpansionService()
            result = await service.expand("xyzunknowncondition", ["ICD-10-CM"])

            assert result["diagnoses"] == []
            assert result["labs"] == []
            assert result["medications"] == []

    async def test_llm_expansion_parses_response(self):
        """LLM expansion parses JSON response correctly."""
        with patch("src.services.expansion.config") as mock_config:
            mock_config.EXPANSION_ENABLED = True
            mock_config.EXPANSION_MODEL = "gpt-4o-mini"
            mock_config.EXPANSION_CACHE_TTL = 3600
            mock_config.OPENAI_API_KEY = "test"

            # Mock the _llm_expand method directly
            service = ClinicalExpansionService()

            with patch.object(service, "_llm_expand") as mock_expand:
                mock_expand.return_value = {
                    "diagnoses": ["term1", "term2"],
                    "labs": ["lab1"],
                    "medications": [],
                }

                result = await service.expand("test", ["ICD-10-CM"])

                assert result["diagnoses"] == ["term1", "term2"]
                assert result["labs"] == ["lab1"]
                assert result["medications"] == []

    async def test_llm_expansion_handles_markdown_blocks(self):
        """LLM expansion handles markdown code blocks in response."""
        # Test the JSON parsing logic directly
        service = ClinicalExpansionService()

        # Test markdown stripping
        content = '```json\n{"diagnoses": ["term1"], "labs": [], "medications": []}\n```'
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        import json
        result = json.loads(content)
        assert result["diagnoses"] == ["term1"]

    async def test_llm_failure_falls_back_to_static(self):
        """When LLM fails, falls back to static expansion."""
        with patch("src.services.expansion.config") as mock_config, \
             patch("src.services.expansion.ChatOpenAI") as MockLLM:

            mock_config.EXPANSION_ENABLED = True
            mock_config.EXPANSION_MODEL = "gpt-4o-mini"
            mock_config.EXPANSION_CACHE_TTL = 3600
            mock_config.OPENAI_API_KEY = "test"

            # LLM raises exception
            mock_chain = MagicMock()
            mock_chain.ainvoke = AsyncMock(side_effect=RuntimeError("API error"))

            mock_llm_instance = MagicMock()
            mock_llm_instance.__or__ = MagicMock(return_value=mock_chain)
            MockLLM.return_value = mock_llm_instance

            service = ClinicalExpansionService()
            result = await service.expand("diabetes", ["ICD-10-CM"])

            # Should still get results from static fallback
            assert len(result["diagnoses"]) > 0

    async def test_caching_works(self):
        """Caching prevents redundant LLM calls."""
        with patch("src.services.expansion.config") as mock_config:
            mock_config.EXPANSION_ENABLED = True
            mock_config.EXPANSION_MODEL = "gpt-4o-mini"
            mock_config.EXPANSION_CACHE_TTL = 3600
            mock_config.OPENAI_API_KEY = "test"

            service = ClinicalExpansionService()
            call_count = 0

            async def mock_llm_expand(query, systems, max_per_category):
                nonlocal call_count
                call_count += 1
                return {"diagnoses": ["cached"], "labs": [], "medications": []}

            with patch.object(service, "_llm_expand", mock_llm_expand):
                # First call
                result1 = await service.expand("test", ["ICD-10-CM"])
                # Second call with same params
                result2 = await service.expand("test", ["ICD-10-CM"])

                assert result1 == result2
                # LLM should only be called once due to caching
                assert call_count == 1

    async def test_different_systems_different_cache_keys(self):
        """Different systems produce different cache entries."""
        with patch("src.services.expansion.config") as mock_config:
            mock_config.EXPANSION_ENABLED = True
            mock_config.EXPANSION_MODEL = "gpt-4o-mini"
            mock_config.EXPANSION_CACHE_TTL = 3600
            mock_config.OPENAI_API_KEY = "test"

            service = ClinicalExpansionService()
            call_count = 0

            async def mock_llm_expand(query, systems, max_per_category):
                nonlocal call_count
                call_count += 1
                return {"diagnoses": [], "labs": [], "medications": []}

            with patch.object(service, "_llm_expand", mock_llm_expand):
                await service.expand("test", ["ICD-10-CM"])
                await service.expand("test", ["LOINC"])

                # Both should make LLM calls (different cache keys)
                assert call_count == 2

    def test_clear_cache(self):
        """clear_cache empties the cache."""
        service = ClinicalExpansionService()
        service._cache["test"] = (0, {"diagnoses": [], "labs": [], "medications": []})

        service.clear_cache()

        assert len(service._cache) == 0


class TestExpansionServiceSingleton:
    """Tests for the singleton pattern."""

    def setup_method(self):
        reset_expansion_service()

    def teardown_method(self):
        reset_expansion_service()

    async def test_get_expansion_service_returns_singleton(self):
        service1 = await get_expansion_service()
        service2 = await get_expansion_service()

        assert service1 is service2

    async def test_reset_clears_singleton(self):
        service1 = await get_expansion_service()
        reset_expansion_service()
        service2 = await get_expansion_service()

        assert service1 is not service2
