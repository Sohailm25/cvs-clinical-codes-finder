# ABOUTME: Tests for NLP parsing and ambiguity detection.
# ABOUTME: Verifies entity extraction and clarification logic.

import pytest
from src.agent.parsing import (
    ParsedQuery,
    parse_query,
    needs_clarification,
    get_clarification_options,
)


class TestParsedQuery:
    """Tests for ParsedQuery model."""

    def test_primary_intent_returns_highest_score(self):
        """primary_intent should return the intent with highest score."""
        parsed = ParsedQuery(
            intent_diagnosis=0.2,
            intent_laboratory=0.6,
            intent_medication=0.1,
        )
        assert parsed.primary_intent == "laboratory"

    def test_intent_scores_dict_format(self):
        """intent_scores_dict should match IntentScores format."""
        parsed = ParsedQuery(
            intent_diagnosis=0.5,
            intent_laboratory=0.3,
            intent_medication=0.1,
            intent_supplies=0.05,
            intent_units=0.03,
            intent_phenotype=0.02,
        )
        scores = parsed.intent_scores_dict
        assert "diagnosis" in scores
        assert "supply_service" in scores  # Note: supplies maps to supply_service
        assert "unit" in scores  # Note: units maps to unit
        assert scores["diagnosis"] == 0.5


class TestNeedsClarification:
    """Tests for ambiguity detection."""

    def test_clear_intent_no_clarification(self):
        """Clear intent should not need clarification."""
        parsed = ParsedQuery(
            intent_diagnosis=0.8,
            intent_laboratory=0.1,
        )
        assert not needs_clarification(parsed)

    def test_ambiguous_intent_needs_clarification(self):
        """Ambiguous intent (close scores, no dominant) should need clarification."""
        parsed = ParsedQuery(
            intent_diagnosis=0.4,
            intent_laboratory=0.35,
            intent_medication=0.25,
        )
        assert needs_clarification(parsed)

    def test_moderate_gap_no_clarification(self):
        """Moderate gap between top scores should not need clarification."""
        parsed = ParsedQuery(
            intent_diagnosis=0.55,
            intent_laboratory=0.35,
        )
        assert not needs_clarification(parsed)

    def test_high_top_score_no_clarification_despite_close_second(self):
        """High top score shouldn't need clarification even if gap is small."""
        parsed = ParsedQuery(
            intent_diagnosis=0.65,
            intent_laboratory=0.55,
        )
        # Gap is 0.1 (< 0.15) but top is >= 0.6
        assert not needs_clarification(parsed)

    def test_custom_threshold(self):
        """Custom gap threshold should be respected."""
        parsed = ParsedQuery(
            intent_diagnosis=0.45,
            intent_laboratory=0.40,
        )
        # Gap is 0.05
        assert needs_clarification(parsed, gap_threshold=0.10)
        assert not needs_clarification(parsed, gap_threshold=0.03)


class TestGetClarificationOptions:
    """Tests for clarification option generation."""

    def test_returns_top_intents(self):
        """Should return options for intents above threshold."""
        parsed = ParsedQuery(
            intent_diagnosis=0.4,
            intent_laboratory=0.35,
            intent_medication=0.15,
            intent_phenotype=0.05,
        )
        options = get_clarification_options(parsed, threshold=0.2)

        # Should include diagnosis and laboratory (above 0.2)
        intents = [o["intent"] for o in options]
        assert "diagnosis" in intents
        assert "laboratory" in intents
        # Should not include phenotype (below 0.2)
        assert "phenotype" not in intents

    def test_options_sorted_by_score(self):
        """Options should be sorted by score descending."""
        parsed = ParsedQuery(
            intent_laboratory=0.4,
            intent_diagnosis=0.35,
            intent_medication=0.25,
        )
        options = get_clarification_options(parsed, threshold=0.2)

        # Laboratory should be first (highest)
        assert options[0]["intent"] == "laboratory"
        assert options[1]["intent"] == "diagnosis"

    def test_max_three_options(self):
        """Should return at most 3 options."""
        parsed = ParsedQuery(
            intent_diagnosis=0.25,
            intent_laboratory=0.25,
            intent_medication=0.25,
            intent_supplies=0.25,
        )
        options = get_clarification_options(parsed, threshold=0.2)
        assert len(options) <= 3

    def test_options_have_labels(self):
        """Each option should have both intent and label."""
        parsed = ParsedQuery(intent_diagnosis=0.5, intent_laboratory=0.4)
        options = get_clarification_options(parsed)

        for opt in options:
            assert "intent" in opt
            assert "label" in opt
            assert len(opt["label"]) > 0


class TestParseQuery:
    """Integration tests for parse_query function."""

    @pytest.mark.asyncio
    async def test_parses_medication_query(self):
        """Should extract medication entities from drug query."""
        parsed = await parse_query("metformin 500 mg")

        # Should identify as medication
        assert parsed.intent_medication > 0.3

    @pytest.mark.asyncio
    async def test_parses_diagnosis_query(self):
        """Should classify diagnosis query correctly."""
        parsed = await parse_query("diabetes mellitus type 2")

        assert parsed.intent_diagnosis > 0.3

    @pytest.mark.asyncio
    async def test_parses_lab_query(self):
        """Should classify lab test query correctly."""
        parsed = await parse_query("blood glucose level")

        assert parsed.intent_laboratory > 0.3

    @pytest.mark.asyncio
    async def test_ambiguous_query_has_reason(self):
        """Ambiguous query should potentially have ambiguity_reason."""
        # "blood sugar" could be lab or diagnosis
        parsed = await parse_query("blood sugar")

        # Should have some intent scores
        total = (
            parsed.intent_diagnosis
            + parsed.intent_laboratory
            + parsed.intent_medication
        )
        assert total > 0
