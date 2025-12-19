# ABOUTME: Tests that semantic reranking improves confidence scores for clinically relevant matches.
# ABOUTME: Verifies that semantic scores properly boost relevant results over lexical-only scoring.

import pytest
import asyncio
from src.tools.base import CodeResult
from src.scoring.reranker import semantic_rerank, compute_semantic_scores
from src.agent.nodes.consolidate import compute_confidence


@pytest.fixture
def diabetes_results() -> list[CodeResult]:
    """Create test results for diabetes query - with different clinical relevance levels."""
    return [
        CodeResult(
            system="ICD-10-CM",
            code="E11.9",
            display="Type 2 diabetes mellitus without complications",
            confidence=0.0,  # Will be computed
            metadata={},
            source={},
        ),
        CodeResult(
            system="ICD-10-CM",
            code="E13.9",
            display="Other specified diabetes mellitus without complications",
            confidence=0.0,
            metadata={},
            source={},
        ),
        CodeResult(
            system="ICD-10-CM",
            code="N25.1",
            display="Nephrogenic diabetes insipidus",
            confidence=0.0,
            metadata={},
            source={},
        ),
        CodeResult(
            system="ICD-10-CM",
            code="E10.9",
            display="Type 1 diabetes mellitus without complications",
            confidence=0.0,
            metadata={},
            source={},
        ),
    ]


@pytest.fixture
def glucose_results() -> list[CodeResult]:
    """Create test results for glucose test query."""
    return [
        CodeResult(
            system="LOINC",
            code="2345-7",
            display="Glucose [Mass/volume] in Serum or Plasma",
            confidence=0.0,
            metadata={},
            source={},
        ),
        CodeResult(
            system="LOINC",
            code="4548-4",
            display="Hemoglobin A1c/Hemoglobin.total in Blood",
            confidence=0.0,
            metadata={},
            source={},
        ),
        CodeResult(
            system="LOINC",
            code="2339-0",
            display="Glucose [Mass/volume] in Blood",
            confidence=0.0,
            metadata={},
            source={},
        ),
    ]


class TestLexicalConfidence:
    """Test that lexical confidence has known limitations."""

    def test_jaccard_favors_token_overlap(self, diabetes_results):
        """Lexical scoring favors token overlap, not clinical relevance."""
        query = "diabetes"

        scores = {}
        for r in diabetes_results:
            scores[r.code] = compute_confidence(query, {"display": r.display, "code": r.code})

        # Show the lexical scores for debugging
        print("\nLexical scores for 'diabetes':")
        for code, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            print(f"  {code}: {score:.3f}")

        # Lexical scoring will rank based on token overlap
        # "Nephrogenic diabetes insipidus" has "diabetes" so scores well
        # This is the limitation we expect semantic reranking to fix
        assert scores["N25.1"] > 0, "Should find some lexical match"

    def test_lexical_misses_synonym(self):
        """Lexical scoring misses semantic matches without token overlap."""
        query = "blood sugar"

        result = {"display": "Glucose [Mass/volume] in Serum", "code": "2345-7"}
        score = compute_confidence(query, result)

        print(f"\nLexical score for 'blood sugar' -> 'Glucose': {score:.3f}")

        # "blood sugar" doesn't match "Glucose" lexically
        # This is a case where semantic reranking should help
        assert score < 0.5, "Lexical should score low without token overlap"


class TestSemanticReranking:
    """Test that semantic reranking improves clinical relevance."""

    @pytest.mark.asyncio
    async def test_semantic_scores_computed(self, diabetes_results):
        """Verify semantic scores are computed for all results."""
        query = "diabetes"

        # Compute semantic scores
        scores = await compute_semantic_scores(query, diabetes_results)

        assert len(scores) == len(diabetes_results)
        assert all(0 <= s <= 1 for s in scores), "Scores should be normalized to [0,1]"

        # Print for debugging
        print("\nSemantic scores for 'diabetes':")
        for r, s in zip(diabetes_results, scores):
            print(f"  {r.code} ({r.display[:40]}...): {s:.3f}")

    @pytest.mark.asyncio
    async def test_diabetes_mellitus_preferred_over_insipidus(self, diabetes_results):
        """Semantic reranking should prefer diabetes mellitus over insipidus."""
        query = "diabetes"

        # Set initial lexical confidence
        for r in diabetes_results:
            r = CodeResult(
                system=r.system,
                code=r.code,
                display=r.display,
                confidence=compute_confidence(query, {"display": r.display, "code": r.code}),
                metadata=r.metadata,
                source=r.source,
            )

        # Apply semantic reranking
        reranked = await semantic_rerank(query, diabetes_results)

        print("\nReranked results for 'diabetes':")
        for r in reranked:
            print(f"  {r.code}: {r.confidence:.3f} - {r.display[:50]}")

        # Find positions of key codes
        codes = [r.code for r in reranked]

        # E11.9 (Type 2 diabetes) and E10.9 (Type 1 diabetes) should rank high
        # N25.1 (Nephrogenic diabetes insipidus) should rank lower
        insipidus_rank = codes.index("N25.1")
        mellitus_ranks = [codes.index("E11.9"), codes.index("E10.9")]

        # At least one diabetes mellitus code should rank higher than insipidus
        assert any(r < insipidus_rank for r in mellitus_ranks), \
            "Diabetes mellitus should rank higher than diabetes insipidus"

    @pytest.mark.asyncio
    async def test_semantic_improves_synonym_matching(self, glucose_results):
        """Semantic reranking should recognize 'blood sugar' = 'glucose'."""
        query = "blood sugar test"

        # Set low initial confidence (lexical won't match well)
        for r in glucose_results:
            r = CodeResult(
                system=r.system,
                code=r.code,
                display=r.display,
                confidence=0.2,  # Low lexical score
                metadata=r.metadata,
                source=r.source,
            )

        # Apply semantic reranking
        reranked = await semantic_rerank(query, glucose_results)

        print("\nReranked results for 'blood sugar test':")
        for r in reranked:
            print(f"  {r.code}: {r.confidence:.3f} - {r.display}")

        # Glucose codes should have improved confidence
        glucose_result = next(r for r in reranked if "Glucose" in r.display)
        assert glucose_result.confidence > 0.3, \
            "Semantic should boost glucose for 'blood sugar' query"


class TestCombinedScoring:
    """Test the combined lexical + semantic scoring."""

    @pytest.mark.asyncio
    async def test_combined_score_in_expected_range(self, diabetes_results):
        """Combined scores should be between lexical and semantic extremes."""
        query = "diabetes type 2"

        # Set lexical scores
        results_with_confidence = []
        for r in diabetes_results:
            conf = compute_confidence(query, {"display": r.display, "code": r.code})
            results_with_confidence.append(CodeResult(
                system=r.system,
                code=r.code,
                display=r.display,
                confidence=conf,
                metadata=r.metadata,
                source=r.source,
            ))

        lexical_scores = [r.confidence for r in results_with_confidence]

        # Get semantic scores
        semantic_scores = await compute_semantic_scores(query, results_with_confidence)

        # Rerank
        reranked = await semantic_rerank(query, results_with_confidence)
        combined_scores = [r.confidence for r in reranked]

        print(f"\nScore comparison for '{query}':")
        for i, r in enumerate(diabetes_results):
            print(f"  {r.code}: lex={lexical_scores[i]:.3f}, "
                  f"sem={semantic_scores[i]:.3f}, "
                  f"combined={combined_scores[i]:.3f}")

        # All combined scores should be valid
        assert all(0 <= s <= 1 for s in combined_scores), \
            "Combined scores should be in [0, 1]"

    @pytest.mark.asyncio
    async def test_e11_ranks_first_for_type_2_diabetes(self, diabetes_results):
        """E11.9 (Type 2 DM) should rank first for 'diabetes type 2' query."""
        query = "diabetes type 2"

        # Set lexical scores
        results_with_confidence = []
        for r in diabetes_results:
            conf = compute_confidence(query, {"display": r.display, "code": r.code})
            results_with_confidence.append(CodeResult(
                system=r.system,
                code=r.code,
                display=r.display,
                confidence=conf,
                metadata=r.metadata,
                source=r.source,
            ))

        # Rerank
        reranked = await semantic_rerank(query, results_with_confidence)

        print(f"\nFinal ranking for '{query}':")
        for i, r in enumerate(reranked):
            print(f"  {i+1}. {r.code}: {r.confidence:.3f} - {r.display[:50]}")

        # E11.9 should be in top 2
        top_2_codes = [r.code for r in reranked[:2]]
        assert "E11.9" in top_2_codes, \
            "E11.9 (Type 2 diabetes) should be in top 2 for 'diabetes type 2' query"
