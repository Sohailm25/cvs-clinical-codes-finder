# ABOUTME: Integration tests for the Clinical Codes Finder agent.
# ABOUTME: Validates all test prompts from the assignment specification.

import pytest
from src.agent import run_agent


class TestAssignmentPrompts:
    """Test all prompts specified in the assignment."""

    @pytest.mark.asyncio
    async def test_diabetes_returns_icd10(self):
        """'diabetes' should return ICD-10-CM codes."""
        result = await run_agent("diabetes")

        # Should have results
        assert len(result["consolidated_results"]) > 0

        # Should include ICD-10-CM in selected systems
        assert "ICD-10-CM" in result["selected_systems"]

        # Should have ICD-10-CM results
        systems = {r.system for r in result["consolidated_results"]}
        assert "ICD-10-CM" in systems

        # At least one result should mention diabetes
        has_diabetes = any(
            "diabetes" in r.display.lower()
            for r in result["consolidated_results"]
        )
        assert has_diabetes

    @pytest.mark.asyncio
    async def test_glucose_test_returns_loinc(self):
        """'glucose test' should return LOINC codes."""
        result = await run_agent("glucose test")

        assert len(result["consolidated_results"]) > 0
        assert "LOINC" in result["selected_systems"]

        systems = {r.system for r in result["consolidated_results"]}
        assert "LOINC" in systems

        has_glucose = any(
            "glucose" in r.display.lower()
            for r in result["consolidated_results"]
        )
        assert has_glucose

    @pytest.mark.asyncio
    async def test_metformin_returns_rxterms(self):
        """'metformin 500 mg' should return RxTerms codes."""
        result = await run_agent("metformin 500 mg")

        assert len(result["consolidated_results"]) > 0
        assert "RxTerms" in result["selected_systems"]

        systems = {r.system for r in result["consolidated_results"]}
        assert "RxTerms" in systems

        has_metformin = any(
            "metformin" in r.display.lower()
            for r in result["consolidated_results"]
        )
        assert has_metformin

    @pytest.mark.asyncio
    async def test_wheelchair_returns_hcpcs(self):
        """'wheelchair' should return HCPCS codes."""
        result = await run_agent("wheelchair")

        assert len(result["consolidated_results"]) > 0
        assert "HCPCS" in result["selected_systems"]

        systems = {r.system for r in result["consolidated_results"]}
        assert "HCPCS" in systems

        has_wheelchair = any(
            "wheelchair" in r.display.lower()
            for r in result["consolidated_results"]
        )
        assert has_wheelchair

    @pytest.mark.asyncio
    async def test_mg_dl_returns_ucum(self):
        """'mg/dL' should return UCUM codes."""
        result = await run_agent("mg/dL")

        assert len(result["consolidated_results"]) > 0
        assert "UCUM" in result["selected_systems"]

        systems = {r.system for r in result["consolidated_results"]}
        assert "UCUM" in systems

        # Check for mg/dL or similar unit
        has_unit = any(
            "mg" in r.display.lower() or "mg" in r.code.lower()
            for r in result["consolidated_results"]
        )
        assert has_unit

    @pytest.mark.asyncio
    async def test_ataxia_returns_hpo(self):
        """'ataxia' should return HPO codes."""
        result = await run_agent("ataxia")

        assert len(result["consolidated_results"]) > 0
        assert "HPO" in result["selected_systems"]

        systems = {r.system for r in result["consolidated_results"]}
        assert "HPO" in systems

        has_ataxia = any(
            "ataxia" in r.display.lower()
            for r in result["consolidated_results"]
        )
        assert has_ataxia


class TestAgentBehavior:
    """Test general agent behavior and quality."""

    @pytest.mark.asyncio
    async def test_no_hallucinated_codes(self):
        """Agent should never return codes not from the API."""
        result = await run_agent("completely made up term xyzabc123")

        # Results should be empty or very limited
        # If there are results, they should be from actual API responses
        # (The API might return some results via fuzzy matching)
        for r in result["consolidated_results"]:
            # All results should have valid source info
            assert r.source.get("tool") is not None
            assert r.source.get("term_used") is not None

    @pytest.mark.asyncio
    async def test_reasoning_trace_present(self):
        """Agent should always produce a reasoning trace."""
        result = await run_agent("aspirin")

        assert len(result["reasoning_trace"]) > 0
        assert any("Planning" in t or "Classified" in t for t in result["reasoning_trace"])

    @pytest.mark.asyncio
    async def test_summary_present(self):
        """Agent should always produce a summary."""
        result = await run_agent("hypertension")

        assert result["summary"]
        assert len(result["summary"]) > 10

    @pytest.mark.asyncio
    async def test_multi_system_query(self):
        """Complex query should search multiple relevant systems."""
        result = await run_agent("diabetes blood glucose test")

        # Should include both diagnosis and lab systems
        systems = result["selected_systems"]
        assert len(systems) >= 2
