# ABOUTME: Consolidation node for the clinical codes agent.
# ABOUTME: Deduplicates, ranks, and filters results across systems.

from typing import Any

from src.agent.state import AgentState
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
    """Rank results by confidence score."""
    for r in results:
        if "confidence" not in r or r["confidence"] == 0.0:
            r["confidence"] = compute_confidence(query, r)

    return sorted(results, key=lambda x: x.get("confidence", 0), reverse=True)


def consolidate_results(
    raw_results: dict[str, list[dict]],
    query: str,
    top_k_per_system: int = 5,
) -> list[CodeResult]:
    """
    Consolidate results from all systems.

    Steps:
    1. Deduplicate within each system
    2. Compute confidence scores
    3. Rank by confidence
    4. Keep top K per system
    5. Convert to CodeResult objects
    """
    consolidated: list[CodeResult] = []

    for system, results in raw_results.items():
        # Dedupe
        deduped = deduplicate_within_system(results)

        # Rank
        ranked = rank_results(deduped, query)

        # Take top K
        top_results = ranked[:top_k_per_system]

        # Convert to CodeResult
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

    # Group counts for reasoning
    system_counts = {}
    for r in consolidated:
        system_counts[r.system] = system_counts.get(r.system, 0) + 1

    counts_str = ", ".join(f"{s}: {c}" for s, c in system_counts.items())
    reasoning = f"Consolidated to {len(consolidated)} results ({counts_str})"

    return {
        "consolidated_results": consolidated,
        "reasoning_trace": [reasoning],
    }
