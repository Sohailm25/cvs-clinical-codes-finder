# ABOUTME: Consolidation node for the clinical codes agent.
# ABOUTME: Deduplicates, ranks, and filters results across systems.

from typing import Any

from src.agent.multi_hop import fetch_hierarchies_for_results
from src.agent.state import AgentState
from src.config import config
from src.scoring import semantic_rerank
from src.tools.base import CodeResult


def compute_confidence(query: str, result: dict) -> float:
    """
    Compute confidence score for a result.

    Multi-factor scoring:
    - Lexical overlap (Jaccard similarity)
    - Position in API results (earlier = better)
    - Code specificity (longer codes often more specific)
    """
    query_tokens = set(query.lower().split())
    display = result.get("display", "")
    display_tokens = set(display.lower().split())

    # Jaccard similarity
    intersection = len(query_tokens & display_tokens)
    union = len(query_tokens | display_tokens)
    jaccard = intersection / union if union > 0 else 0.0

    # Exact substring match bonus
    exact_match_bonus = 0.0
    if query.lower() in display.lower():
        exact_match_bonus = 0.3
    elif display.lower() in query.lower():
        exact_match_bonus = 0.2

    # Code specificity (longer = more specific, up to a point)
    code = result.get("code", "")
    specificity = min(len(code) / 10.0, 0.3)

    # Weighted combination
    confidence = (
        jaccard * 0.4 +
        exact_match_bonus +
        specificity
    )

    return min(confidence, 1.0)


def deduplicate_within_system(results: list[dict]) -> list[dict]:
    """Remove duplicate codes within a single system."""
    seen_codes: set[str] = set()
    deduped: list[dict] = []

    for r in results:
        code = r.get("code", "")
        if code and code not in seen_codes:
            seen_codes.add(code)
            deduped.append(r)

    return deduped


def rank_results(results: list[dict], query: str) -> list[dict]:
    """Rank results by confidence score.

    Uses the search_term that found each result (if available) for more accurate scoring.
    """
    for r in results:
        if "confidence" not in r or r["confidence"] == 0.0:
            # Use the specific search term that found this result, fallback to query
            match_term = r.get("search_term", query)
            r["confidence"] = compute_confidence(match_term, r)

    return sorted(results, key=lambda x: x.get("confidence", 0), reverse=True)


def consolidate_results(
    raw_results: dict[str, list[dict]],
    query: str,
    top_k_per_system: int = 5,
    min_confidence: float | None = None,
) -> list[CodeResult]:
    """
    Consolidate results from all systems.

    Steps:
    1. Deduplicate within each system
    2. Group by search_term to ensure representation from each term
    3. Compute confidence scores
    4. Filter out low-confidence results (below min_confidence)
    5. Take top K per search_term (or per system if no search_term)
    6. Convert to CodeResult objects
    """
    consolidated: list[CodeResult] = []

    # Confidence thresholds
    HIGH_CONFIDENCE = 0.5   # Results above this are high quality
    MIN_CONFIDENCE = min_confidence if min_confidence is not None else config.CONFIDENCE_THRESHOLD

    for system, results in raw_results.items():
        # Dedupe
        deduped = deduplicate_within_system(results)

        # Group by search_term to ensure representation from each search term
        by_term: dict[str, list[dict]] = {}
        for r in deduped:
            term = r.get("search_term", "_default")
            if term not in by_term:
                by_term[term] = []
            by_term[term].append(r)

        # If multiple search terms, allocate slots proportionally
        num_terms = len(by_term)
        if num_terms > 1:
            # Ensure at least 2-3 results per term
            base_k_per_term = max(3, top_k_per_system // num_terms)
        else:
            base_k_per_term = top_k_per_system

        # Rank and take top K from each term (adaptive based on confidence)
        for term, term_results in by_term.items():
            ranked = rank_results(term_results, query)

            # FILTER: Remove low-confidence results (noise)
            filtered = [r for r in ranked if r.get("confidence", 0) >= MIN_CONFIDENCE]

            # If all results are below threshold, keep the best one (if any exist)
            if not filtered and ranked:
                best = ranked[0]
                # Only keep best if it's at least marginally relevant
                if best.get("confidence", 0) >= MIN_CONFIDENCE * 0.5:
                    filtered = [best]

            # Adaptive limit: show more results if they're high quality
            high_conf_results = [r for r in filtered if r.get("confidence", 0) > HIGH_CONFIDENCE]

            if len(high_conf_results) > base_k_per_term:
                # Extend limit for high-confidence matches (up to 2x)
                k_per_term = min(len(high_conf_results), base_k_per_term * 2)
            else:
                k_per_term = base_k_per_term

            top_results = filtered[:k_per_term]

            for r in top_results:
                consolidated.append(CodeResult(
                    system=system,
                    code=r["code"],
                    display=r.get("display", ""),
                    confidence=r.get("confidence", 0.0),
                    metadata=r.get("metadata", {}),
                    source=r.get("source", {}),
                ))

    # Sort all results by confidence
    consolidated.sort(key=lambda x: x.confidence, reverse=True)

    return consolidated


async def consolidate_node(state: AgentState) -> dict[str, Any]:
    """
    LangGraph node: Consolidate, dedupe, and rank all results.
    """
    raw_results = state.get("raw_results", {})
    query = state["query"]

    consolidated = consolidate_results(raw_results, query)

    # Apply semantic reranking if enabled
    reasoning_parts = []
    if config.SEMANTIC_RERANK_ENABLED and consolidated:
        consolidated = await semantic_rerank(query, consolidated)
        reasoning_parts.append("applied semantic reranking")

    # Fetch hierarchy info for ICD-10 codes
    hierarchy_info = await fetch_hierarchies_for_results(consolidated)

    # Group counts for reasoning
    system_counts = {}
    for r in consolidated:
        system_counts[r.system] = system_counts.get(r.system, 0) + 1

    counts_str = ", ".join(f"{s}: {c}" for s, c in system_counts.items())
    reasoning = f"Consolidated to {len(consolidated)} results ({counts_str})"
    if reasoning_parts:
        reasoning += f", {', '.join(reasoning_parts)}"
    if hierarchy_info:
        reasoning += f", fetched {len(hierarchy_info)} parent codes"

    return {
        "consolidated_results": consolidated,
        "hierarchy_info": hierarchy_info,
        "reasoning_trace": [reasoning],
    }
