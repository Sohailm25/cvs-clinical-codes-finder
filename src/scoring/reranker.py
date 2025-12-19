# ABOUTME: Cross-encoder semantic reranking for clinical code results.
# ABOUTME: Combines semantic similarity with lexical scoring for improved precision.

import asyncio
import logging
import math
from typing import TYPE_CHECKING

from src.config import config

if TYPE_CHECKING:
    from src.tools.base import CodeResult

logger = logging.getLogger(__name__)


def sigmoid(x: float) -> float:
    """Apply sigmoid to normalize raw scores to [0, 1]."""
    return 1 / (1 + math.exp(-x))


async def compute_semantic_scores(
    query: str,
    results: list["CodeResult"],
    model_name: str | None = None,
) -> list[float]:
    """
    Compute semantic similarity scores using cross-encoder.

    Args:
        query: The search query.
        results: List of CodeResult objects to score.
        model_name: Optional model override.

    Returns:
        List of normalized scores [0, 1] for each result.
    """
    if not results:
        return []

    from src.scoring.model_cache import ModelCache

    cache = await ModelCache.get_instance()
    model = await cache.get_model(model_name)

    # Build pairs for cross-encoder
    pairs = [(query, f"{r.code}: {r.display}") for r in results]

    # Score in thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    raw_scores = await loop.run_in_executor(
        None, model.predict, pairs
    )

    # Normalize with sigmoid
    return [sigmoid(float(score)) for score in raw_scores]


def combine_scores(
    lexical_scores: list[float],
    semantic_scores: list[float],
    lexical_weight: float | None = None,
    semantic_weight: float | None = None,
) -> list[float]:
    """
    Combine lexical and semantic scores with configurable weights.

    Args:
        lexical_scores: Original lexical/heuristic confidence scores.
        semantic_scores: Semantic similarity scores from cross-encoder.
        lexical_weight: Weight for lexical scores (default from config).
        semantic_weight: Weight for semantic scores (default from config).

    Returns:
        Combined weighted scores.
    """
    lw = lexical_weight if lexical_weight is not None else config.RERANKER_WEIGHT_LEXICAL
    sw = semantic_weight if semantic_weight is not None else config.RERANKER_WEIGHT_SEMANTIC

    # Normalize weights
    total = lw + sw
    lw = lw / total
    sw = sw / total

    combined = []
    for lex, sem in zip(lexical_scores, semantic_scores):
        combined.append(lw * lex + sw * sem)

    return combined


async def semantic_rerank(
    query: str,
    results: list["CodeResult"],
    model_name: str | None = None,
) -> list["CodeResult"]:
    """
    Rerank results using cross-encoder semantic similarity.

    Combines original lexical confidence with semantic scores,
    then re-sorts results by combined score.

    Args:
        query: The search query.
        results: List of CodeResult objects to rerank.
        model_name: Optional model override.

    Returns:
        Reranked list of CodeResult objects with updated confidence scores.
    """
    if not results:
        return []

    if not config.SEMANTIC_RERANK_ENABLED:
        logger.debug("Semantic reranking disabled, returning original order")
        return results

    try:
        # Get semantic scores
        semantic_scores = await compute_semantic_scores(query, results, model_name)

        # Get original lexical scores
        lexical_scores = [r.confidence for r in results]

        # Combine scores
        combined = combine_scores(lexical_scores, semantic_scores)

        # Create new results with updated confidence
        from dataclasses import replace
        reranked = []
        for result, new_confidence in zip(results, combined):
            reranked.append(replace(result, confidence=new_confidence))

        # Sort by new confidence
        reranked.sort(key=lambda x: x.confidence, reverse=True)

        logger.debug(f"Reranked {len(results)} results with semantic scores")
        return reranked

    except Exception as e:
        logger.warning(f"Semantic reranking failed, returning original order: {e}")
        return results


async def semantic_rerank_by_system(
    query: str,
    results: list["CodeResult"],
    model_name: str | None = None,
) -> list["CodeResult"]:
    """
    Rerank results within each system, then combine.

    This preserves system diversity while improving intra-system ranking.

    Args:
        query: The search query.
        results: List of CodeResult objects to rerank.
        model_name: Optional model override.

    Returns:
        Reranked results with system diversity preserved.
    """
    if not results:
        return []

    if not config.SEMANTIC_RERANK_ENABLED:
        return results

    # Group by system
    by_system: dict[str, list["CodeResult"]] = {}
    for r in results:
        if r.system not in by_system:
            by_system[r.system] = []
        by_system[r.system].append(r)

    # Rerank each system independently
    reranked_by_system = {}
    for system, system_results in by_system.items():
        reranked_by_system[system] = await semantic_rerank(
            query, system_results, model_name
        )

    # Interleave results to maintain system diversity
    all_reranked = []
    for system_results in reranked_by_system.values():
        all_reranked.extend(system_results)

    # Final sort by confidence
    all_reranked.sort(key=lambda x: x.confidence, reverse=True)

    return all_reranked
