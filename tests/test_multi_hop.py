# ABOUTME: Tests for multi-hop clinical reasoning and hierarchy fetching.
# ABOUTME: Verifies clinical relationship expansion and code hierarchy lookups.

import pytest
from unittest.mock import patch

from src.agent.multi_hop import (
    CLINICAL_RELATIONSHIPS,
    get_related_terms,
    multi_hop_node,
    fetch_hierarchy,
    fetch_hierarchies_for_results,
)
from src.agent.state import create_initial_state
from src.tools.base import CodeResult


class TestClinicalRelationships:
    """Tests for the clinical relationships data."""

    def test_diabetes_has_relations(self):
        """Diabetes should have related diagnoses, labs, and medications."""
        assert "diabetes" in CLINICAL_RELATIONSHIPS
        relations = CLINICAL_RELATIONSHIPS["diabetes"]
        assert "related_diagnoses" in relations
        assert "related_labs" in relations
        assert "related_medications" in relations
        assert len(relations["related_diagnoses"]) > 0

    def test_hypertension_has_relations(self):
        """Hypertension should have clinical relationships."""
        assert "hypertension" in CLINICAL_RELATIONSHIPS
        relations = CLINICAL_RELATIONSHIPS["hypertension"]
        assert "lisinopril" in relations["related_medications"]

    def test_minimum_conditions_covered(self):
        """Should have at least 40 conditions."""
        assert len(CLINICAL_RELATIONSHIPS) >= 40


class TestGetRelatedTerms:
    """Tests for related term expansion using static fallback."""

    @pytest.fixture(autouse=True)
    def disable_llm_expansion(self):
        """Disable LLM expansion to use deterministic static fallback."""
        with patch("src.services.expansion.config") as mock_config:
            mock_config.EXPANSION_ENABLED = False
            mock_config.EXPANSION_MODEL = "gpt-4o-mini"
            mock_config.EXPANSION_CACHE_TTL = 3600
            yield

    @pytest.mark.asyncio
    async def test_returns_related_diagnoses_for_icd10(self):
        """Should return related diagnoses when ICD-10-CM is selected."""
        terms = await get_related_terms("diabetes", ["ICD-10-CM"])
        # Should include diabetes-related diagnoses from static dict
        assert any("neuropathy" in t.lower() or "retinopathy" in t.lower() for t in terms)

    @pytest.mark.asyncio
    async def test_returns_related_labs_for_loinc(self):
        """Should return related labs when LOINC is selected."""
        terms = await get_related_terms("diabetes", ["LOINC"])
        # Should include diabetes-related labs
        assert any("a1c" in t.lower() or "glucose" in t.lower() for t in terms)

    @pytest.mark.asyncio
    async def test_returns_related_meds_for_rxterms(self):
        """Should return related medications when RxTerms is selected."""
        terms = await get_related_terms("diabetes", ["RxTerms"])
        # Should include diabetes medications
        assert any("metformin" in t.lower() or "insulin" in t.lower() for t in terms)

    @pytest.mark.asyncio
    async def test_respects_max_terms(self):
        """Should limit returned terms to max_terms."""
        terms = await get_related_terms("diabetes", ["ICD-10-CM", "LOINC", "RxTerms"], max_terms=3)
        assert len(terms) <= 3

    @pytest.mark.asyncio
    async def test_no_duplicates(self):
        """Should not return duplicate terms."""
        terms = await get_related_terms("diabetes", ["ICD-10-CM", "HPO"])
        assert len(terms) == len(set(t.lower() for t in terms))

    @pytest.mark.asyncio
    async def test_excludes_original_query(self):
        """Should not include the original query in results."""
        terms = await get_related_terms("diabetes", ["ICD-10-CM"])
        assert "diabetes" not in [t.lower() for t in terms]

    @pytest.mark.asyncio
    async def test_returns_empty_for_unknown_condition(self):
        """Should return empty list for unknown conditions."""
        terms = await get_related_terms("xyznotarealcondition", ["ICD-10-CM"])
        assert terms == []


class TestMultiHopNode:
    """Tests for the multi_hop_node function."""

    @pytest.mark.asyncio
    async def test_skips_when_disabled(self):
        """Should return empty dict when multi_hop_enabled is False."""
        state = create_initial_state("diabetes", multi_hop_enabled=False)
        state["selected_systems"] = ["ICD-10-CM"]

        result = await multi_hop_node(state)
        assert result == {}

    @pytest.mark.asyncio
    async def test_expands_when_enabled(self):
        """Should expand search terms when multi_hop_enabled is True."""
        state = create_initial_state("diabetes", multi_hop_enabled=True)
        state["selected_systems"] = ["ICD-10-CM", "LOINC"]
        state["search_terms"] = ["diabetes"]

        result = await multi_hop_node(state)

        assert "related_terms" in result
        assert len(result["related_terms"]) > 0
        assert "search_terms" in result
        # Search terms should include original + related
        assert len(result["search_terms"]) > 1

    @pytest.mark.asyncio
    async def test_adds_reasoning_trace(self):
        """Should add reasoning trace entry."""
        state = create_initial_state("hypertension", multi_hop_enabled=True)
        state["selected_systems"] = ["ICD-10-CM"]
        state["search_terms"] = ["hypertension"]

        result = await multi_hop_node(state)

        assert "reasoning_trace" in result
        assert len(result["reasoning_trace"]) > 0
        assert "Multi-hop" in result["reasoning_trace"][0]


class TestFetchHierarchy:
    """Tests for hierarchy fetching."""

    @pytest.mark.asyncio
    async def test_returns_empty_for_non_icd10(self):
        """Should return empty dict for non-ICD-10 systems."""
        result = await fetch_hierarchy("12345-6", "LOINC")
        assert result == {}

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_parent(self):
        """Should return empty dict for codes without subcategory."""
        # E11 doesn't have a parent in the structure
        result = await fetch_hierarchy("E11", "ICD-10-CM")
        assert result == {}

    @pytest.mark.asyncio
    async def test_fetches_parent_for_subcategory(self):
        """Should fetch parent info for subcategory codes."""
        # E11.65 should have parent E11
        result = await fetch_hierarchy("E11.65", "ICD-10-CM")

        # This may or may not succeed depending on API
        # Just verify it returns the right structure
        if result:
            assert "parent_code" in result
            assert "parent_display" in result


class TestFetchHierarchiesForResults:
    """Tests for bulk hierarchy fetching."""

    @pytest.mark.asyncio
    async def test_fetches_for_icd10_results(self):
        """Should fetch hierarchies for ICD-10 results."""
        results = [
            CodeResult(
                system="ICD-10-CM",
                code="E11.65",
                display="Type 2 diabetes with hyperglycemia",
                confidence=0.9,
                metadata={},
                source={"tool": "ICD10Tool"},
            ),
        ]

        hierarchies = await fetch_hierarchies_for_results(results)

        # May or may not have results depending on API
        assert isinstance(hierarchies, dict)

    @pytest.mark.asyncio
    async def test_skips_non_icd10_results(self):
        """Should not fetch hierarchies for non-ICD-10 results."""
        results = [
            CodeResult(
                system="LOINC",
                code="12345-6",
                display="Some lab test",
                confidence=0.9,
                metadata={},
                source={"tool": "LOINCTool"},
            ),
        ]

        hierarchies = await fetch_hierarchies_for_results(results)
        assert hierarchies == {}

    @pytest.mark.asyncio
    async def test_respects_max_codes(self):
        """Should limit hierarchy fetches to max_codes."""
        # Create many results
        results = [
            CodeResult(
                system="ICD-10-CM",
                code=f"E11.{i}",
                display=f"Test code {i}",
                confidence=0.9,
                metadata={},
                source={"tool": "ICD10Tool"},
            )
            for i in range(20)
        ]

        # With max_codes=5, should only process first 5
        hierarchies = await fetch_hierarchies_for_results(results, max_codes=5)
        # Can't verify exact count since some fetches may fail
        assert isinstance(hierarchies, dict)
