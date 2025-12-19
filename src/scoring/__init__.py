# ABOUTME: Confidence scoring, deduplication, and semantic reranking.
# ABOUTME: Provides deterministic ranking with optional LLM re-ranking.

from src.scoring.model_cache import ModelCache
from src.scoring.reranker import (
    semantic_rerank,
    semantic_rerank_by_system,
    compute_semantic_scores,
    combine_scores,
    sigmoid,
)

__all__ = [
    "ModelCache",
    "semantic_rerank",
    "semantic_rerank_by_system",
    "compute_semantic_scores",
    "combine_scores",
    "sigmoid",
]
