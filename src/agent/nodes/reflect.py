# ABOUTME: Reflection node for the clinical codes agent.
# ABOUTME: Assesses result quality and decides whether to refine search.

from typing import Any

from src.agent.state import AgentState
from src.config import config


def assess_results(raw_results: dict[str, list[dict]], query: str) -> tuple[str, bool, str | None]:
    """
    Assess result quality and determine if refinement is needed.

    Returns: (assessment_text, needs_refinement, refinement_strategy)
    """
    total_results = sum(len(v) for v in raw_results.values())
    systems_with_results = [s for s, r in raw_results.items() if r]

    # No results at all
    if total_results == 0:
        return (
            "No results found for any system",
            True,
            "broaden",
        )

    # Too many results (might be too broad)
    if total_results > 50:
        return (
            f"Found {total_results} results (may be too broad)",
            True,
            "narrow",
        )

    # Check for high-confidence matches
    query_lower = query.lower()
    high_confidence_count = 0

    for system, results in raw_results.items():
        for r in results:
            display_lower = r.get("display", "").lower()
            # Check for strong match
            if query_lower in display_lower or display_lower in query_lower:
                high_confidence_count += 1

    # Good coverage with high confidence
    if high_confidence_count >= 2:
        return (
            f"Found {total_results} results with {high_confidence_count} high-confidence matches",
            False,
            None,
        )

    # Moderate results but no high confidence
    if total_results < 5 and high_confidence_count == 0:
        return (
            f"Found {total_results} results but no high-confidence matches",
            True,
            "broaden",
        )

    # Acceptable results
    return (
        f"Found {total_results} results across {len(systems_with_results)} systems",
        False,
        None,
    )


async def reflect_node(state: AgentState) -> dict[str, Any]:
    """
    LangGraph node: Assess result quality and decide on refinement.

    Checks:
    - Total result count (too few, too many)
    - High-confidence matches
    - Iteration limit
    """
    iteration = state["iteration"]
    raw_results = state.get("raw_results", {})
    query = state["query"]

    # Assess results
    assessment, needs_refinement, strategy = assess_results(raw_results, query)

    # Enforce iteration limit
    if iteration >= config.MAX_ITERATIONS:
        needs_refinement = False
        strategy = None
        assessment += f" (reached max iterations: {config.MAX_ITERATIONS})"

    reasoning = f"Reflection: {assessment}"
    if needs_refinement:
        reasoning += f" → will {strategy}"
    else:
        reasoning += " → proceeding to consolidation"

    return {
        "coverage_assessment": assessment,
        "needs_refinement": needs_refinement,
        "refinement_strategy": strategy,
        "reasoning_trace": [reasoning],
    }


def should_refine(state: AgentState) -> str:
    """
    Conditional edge function: decide whether to refine or consolidate.

    Returns: "refine" or "consolidate"
    """
    if state.get("needs_refinement", False) and state.get("refinement_strategy"):
        return "refine"
    return "consolidate"
