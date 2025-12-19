# ABOUTME: Tests for cross-encoder semantic reranking.
# ABOUTME: Validates score normalization, combination, and reranking logic.

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from src.tools.base import CodeResult
from src.scoring.reranker import (
    sigmoid,
    combine_scores,
    compute_semantic_scores,
    semantic_rerank,
)


class TestSigmoid:
    """Tests for sigmoid normalization."""

    def test_sigmoid_zero(self):
        assert sigmoid(0) == 0.5

    def test_sigmoid_positive(self):
        result = sigmoid(2)
        assert 0.5 < result < 1.0

    def test_sigmoid_negative(self):
        result = sigmoid(-2)
        assert 0 < result < 0.5

    def test_sigmoid_large_positive(self):
        result = sigmoid(10)
        assert result > 0.99

    def test_sigmoid_large_negative(self):
        result = sigmoid(-10)
        assert result < 0.01


class TestCombineScores:
    """Tests for score combination logic."""

    def test_equal_weights(self):
        lexical = [0.8, 0.6]
        semantic = [0.6, 0.8]
        combined = combine_scores(lexical, semantic, 0.5, 0.5)

        assert combined[0] == pytest.approx(0.7)
        assert combined[1] == pytest.approx(0.7)

    def test_lexical_heavy_weights(self):
        lexical = [0.8, 0.4]
        semantic = [0.4, 0.8]
        combined = combine_scores(lexical, semantic, 0.8, 0.2)

        # Lexical dominates
        assert combined[0] > combined[1]

    def test_semantic_heavy_weights(self):
        lexical = [0.8, 0.4]
        semantic = [0.4, 0.8]
        combined = combine_scores(lexical, semantic, 0.2, 0.8)

        # Semantic dominates
        assert combined[0] < combined[1]

    def test_weights_normalized(self):
        """Weights should be normalized even if they don't sum to 1."""
        lexical = [0.6]
        semantic = [0.4]

        # 60/40 split with unnormalized weights
        combined = combine_scores(lexical, semantic, 6, 4)

        expected = 0.6 * 0.6 + 0.4 * 0.4  # 0.36 + 0.16 = 0.52
        assert combined[0] == pytest.approx(expected)


class TestComputeSemanticScores:
    """Tests for semantic score computation."""

    @pytest.fixture
    def sample_results(self):
        return [
            CodeResult(
                system="ICD-10-CM",
                code="E11.9",
                display="Type 2 diabetes mellitus",
                confidence=0.8,
                metadata={},
                source={},
            ),
            CodeResult(
                system="ICD-10-CM",
                code="E10.9",
                display="Type 1 diabetes mellitus",
                confidence=0.6,
                metadata={},
                source={},
            ),
        ]

    async def test_empty_results(self):
        scores = await compute_semantic_scores("diabetes", [])
        assert scores == []

    async def test_returns_normalized_scores(self, sample_results):
        """Scores should be normalized to [0, 1] via sigmoid."""
        with patch("src.scoring.model_cache.ModelCache") as MockCache:
            mock_instance = MagicMock()
            mock_model = MagicMock()
            # Raw scores from cross-encoder (can be any real number)
            mock_model.predict.return_value = [2.5, 1.0]
            mock_instance.get_model = AsyncMock(return_value=mock_model)
            MockCache.get_instance = AsyncMock(return_value=mock_instance)

            scores = await compute_semantic_scores("diabetes", sample_results)

            assert len(scores) == 2
            # All scores should be in [0, 1]
            for score in scores:
                assert 0 <= score <= 1
            # Higher raw score -> higher normalized score
            assert scores[0] > scores[1]


class TestSemanticRerank:
    """Tests for the full reranking pipeline."""

    @pytest.fixture
    def sample_results(self):
        return [
            CodeResult(
                system="ICD-10-CM",
                code="E11.9",
                display="Type 2 diabetes mellitus",
                confidence=0.8,
                metadata={},
                source={},
            ),
            CodeResult(
                system="ICD-10-CM",
                code="E10.9",
                display="Type 1 diabetes mellitus",
                confidence=0.6,
                metadata={},
                source={},
            ),
            CodeResult(
                system="LOINC",
                code="4548-4",
                display="Hemoglobin A1c",
                confidence=0.5,
                metadata={},
                source={},
            ),
        ]

    async def test_rerank_empty_list(self):
        result = await semantic_rerank("test", [])
        assert result == []

    async def test_rerank_disabled(self, sample_results):
        """When disabled, returns original order."""
        with patch("src.scoring.reranker.config") as mock_config:
            mock_config.SEMANTIC_RERANK_ENABLED = False

            result = await semantic_rerank("diabetes", sample_results)

            assert result == sample_results

    async def test_rerank_updates_confidence(self, sample_results):
        """Reranking should update confidence scores."""
        with patch("src.scoring.reranker.config") as mock_config, \
             patch("src.scoring.model_cache.ModelCache") as MockCache:

            mock_config.SEMANTIC_RERANK_ENABLED = True
            mock_config.RERANKER_WEIGHT_LEXICAL = 0.4
            mock_config.RERANKER_WEIGHT_SEMANTIC = 0.6

            mock_instance = MagicMock()
            mock_model = MagicMock()
            # Second result scores higher semantically
            mock_model.predict.return_value = [1.0, 3.0, 0.5]
            mock_instance.get_model = AsyncMock(return_value=mock_model)
            MockCache.get_instance = AsyncMock(return_value=mock_instance)

            result = await semantic_rerank("diabetes", sample_results)

            # Results should be reordered
            assert len(result) == 3
            # Confidence values should be updated (not original)
            original_confidences = {r.code: r.confidence for r in sample_results}
            for r in result:
                assert r.confidence != original_confidences[r.code]

    async def test_rerank_handles_errors(self, sample_results):
        """On error, returns original order."""
        with patch("src.scoring.reranker.config") as mock_config, \
             patch("src.scoring.model_cache.ModelCache") as MockCache:

            mock_config.SEMANTIC_RERANK_ENABLED = True

            mock_instance = MagicMock()
            mock_instance.get_model = AsyncMock(side_effect=RuntimeError("Model load failed"))
            MockCache.get_instance = AsyncMock(return_value=mock_instance)

            result = await semantic_rerank("diabetes", sample_results)

            # Should return original list on error
            assert result == sample_results
