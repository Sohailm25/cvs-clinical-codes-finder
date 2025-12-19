# ABOUTME: Tests for the summary generation node.
# ABOUTME: Validates structured markdown output and formatting.

import pytest

from src.tools.base import CodeResult
from src.agent.nodes.summarize import (
    generate_fallback_summary,
    format_results_for_summary,
    _confidence_label,
    SYSTEM_DESCRIPTIONS,
)


class TestConfidenceLabel:
    """Tests for confidence score to label conversion."""

    def test_high_confidence(self):
        assert _confidence_label(0.7) == "High"
        assert _confidence_label(0.9) == "High"
        assert _confidence_label(1.0) == "High"

    def test_medium_confidence(self):
        assert _confidence_label(0.5) == "Medium"
        assert _confidence_label(0.4) == "Medium"
        assert _confidence_label(0.31) == "Medium"

    def test_low_confidence(self):
        assert _confidence_label(0.3) == "Low"
        assert _confidence_label(0.1) == "Low"
        assert _confidence_label(0.0) == "Low"

    def test_boundary_values(self):
        # At boundaries: 0.6 is medium, >0.6 is high
        assert _confidence_label(0.6) == "Medium"
        assert _confidence_label(0.61) == "High"
        # 0.3 is low, >0.3 is medium
        assert _confidence_label(0.3) == "Low"
        assert _confidence_label(0.301) == "Medium"


class TestFallbackSummary:
    """Tests for the non-LLM fallback summary generator."""

    def test_no_results(self):
        result = generate_fallback_summary("diabetes", [])
        assert result == "No clinical codes found for 'diabetes'."

    def test_single_result_markdown_structure(self):
        results = [
            CodeResult(
                system="ICD-10-CM",
                code="E11.9",
                display="Type 2 diabetes mellitus without complications",
                confidence=0.85,
                metadata={},
                source={"api": "clinical_tables"},
            )
        ]
        result = generate_fallback_summary("diabetes", results)

        # Check markdown structure
        assert "## Summary" in result
        assert "**1 codes**" in result
        assert "### Top Results by System" in result
        assert "**ICD-10-CM**" in result
        assert "### Key Findings" in result
        assert "**E11.9**" in result

    def test_multiple_systems(self):
        results = [
            CodeResult(
                system="ICD-10-CM",
                code="E11.9",
                display="Type 2 diabetes mellitus",
                confidence=0.85,
                metadata={},
                source={},
            ),
            CodeResult(
                system="LOINC",
                code="4548-4",
                display="Hemoglobin A1c",
                confidence=0.75,
                metadata={},
                source={},
            ),
        ]
        result = generate_fallback_summary("diabetes", results)

        assert "2 codes" in result
        assert "2 system" in result
        assert "**ICD-10-CM**" in result
        assert "**LOINC**" in result
        assert "(Diagnosis Codes)" in result
        assert "(Lab Tests)" in result

    def test_table_format(self):
        results = [
            CodeResult(
                system="ICD-10-CM",
                code="E11.9",
                display="Type 2 diabetes",
                confidence=0.85,
                metadata={},
                source={},
            ),
        ]
        result = generate_fallback_summary("diabetes", results)

        assert "| Code | Description | Confidence |" in result
        assert "|------|-------------|------------|" in result
        assert "| E11.9 |" in result
        assert "| High |" in result

    def test_long_description_truncation(self):
        long_display = "A" * 100  # Longer than 60 chars
        results = [
            CodeResult(
                system="ICD-10-CM",
                code="X99",
                display=long_display,
                confidence=0.5,
                metadata={},
                source={},
            ),
        ]
        result = generate_fallback_summary("test", results)

        # Should be truncated with ellipsis
        assert "A" * 60 + "..." in result
        assert long_display not in result

    def test_more_than_five_results_per_system(self):
        results = [
            CodeResult(
                system="ICD-10-CM",
                code=f"E11.{i}",
                display=f"Diabetes variant {i}",
                confidence=0.8 - i * 0.05,
                metadata={},
                source={},
            )
            for i in range(8)
        ]
        result = generate_fallback_summary("diabetes", results)

        # Should show top 5 and indicate more
        assert "E11.0" in result
        assert "E11.4" in result
        assert "E11.5" not in result  # Should be truncated
        assert "...and 3 more" in result

    def test_primary_match_highlighted(self):
        results = [
            CodeResult(
                system="ICD-10-CM",
                code="E11.9",
                display="Primary diagnosis",
                confidence=0.9,
                metadata={},
                source={},
            ),
            CodeResult(
                system="ICD-10-CM",
                code="E11.65",
                display="Secondary diagnosis",
                confidence=0.7,
                metadata={},
                source={},
            ),
        ]
        result = generate_fallback_summary("diabetes", results)

        # Primary match should be first result (E11.9)
        assert "**Primary match**: **E11.9**" in result


class TestFormatResultsForSummary:
    """Tests for the LLM prompt formatting function."""

    def test_empty_results(self):
        result = format_results_for_summary([])
        assert result == "No results found"

    def test_single_system(self):
        results = [
            CodeResult(
                system="ICD-10-CM",
                code="E11.9",
                display="Type 2 diabetes",
                confidence=0.85,
                metadata={},
                source={},
            ),
        ]
        result = format_results_for_summary(results)

        assert "ICD-10-CM (Diagnosis Codes):" in result
        assert "Code: E11.9" in result
        assert "Display: Type 2 diabetes" in result
        assert "Confidence: High (0.85)" in result

    def test_multiple_systems(self):
        results = [
            CodeResult(
                system="ICD-10-CM",
                code="E11.9",
                display="Type 2 diabetes",
                confidence=0.85,
                metadata={},
                source={},
            ),
            CodeResult(
                system="LOINC",
                code="4548-4",
                display="Hemoglobin A1c",
                confidence=0.75,
                metadata={},
                source={},
            ),
        ]
        result = format_results_for_summary(results)

        assert "ICD-10-CM (Diagnosis Codes):" in result
        assert "LOINC (Lab Tests):" in result

    def test_more_than_five_per_system(self):
        results = [
            CodeResult(
                system="ICD-10-CM",
                code=f"E11.{i}",
                display=f"Variant {i}",
                confidence=0.8,
                metadata={},
                source={},
            )
            for i in range(8)
        ]
        result = format_results_for_summary(results)

        # Should show first 5 and indicate more
        assert "E11.0" in result
        assert "E11.4" in result
        assert "and 3 more results" in result


class TestSystemDescriptions:
    """Tests for system description mapping."""

    def test_all_known_systems(self):
        expected_systems = ["ICD-10-CM", "LOINC", "RxTerms", "HCPCS", "UCUM", "HPO"]
        for system in expected_systems:
            assert system in SYSTEM_DESCRIPTIONS

    def test_descriptions_are_descriptive(self):
        # Each description should provide context
        assert "Diagnosis" in SYSTEM_DESCRIPTIONS["ICD-10-CM"]
        assert "Lab" in SYSTEM_DESCRIPTIONS["LOINC"]
        assert "Medication" in SYSTEM_DESCRIPTIONS["RxTerms"]
