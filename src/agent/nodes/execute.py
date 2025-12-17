# ABOUTME: Execution node for the clinical codes agent.
# ABOUTME: Runs parallel API calls to selected coding systems.

import asyncio
from typing import Any

from src.agent.state import AgentState
from src.tools import ICD10Tool, LOINCTool, RxTermsTool, HCPCSTool, UCUMTool, HPOTool
from src.tools.base import CodeResult, APIError
from src.config import config


# Tool instances
TOOLS = {
    "ICD-10-CM": ICD10Tool(),
    "LOINC": LOINCTool(),
    "RxTerms": RxTermsTool(),
    "HCPCS": HCPCSTool(),
    "UCUM": UCUMTool(),
    "HPO": HPOTool(),
}


async def execute_search(
    system: str,
    term: str,
    max_results: int = 10,
) -> tuple[str, str, list[CodeResult], str | None]:
    """
    Execute a single search and return results.

    Returns: (system, term, results, error_message)
    """
    tool = TOOLS.get(system)
    if not tool:
        return system, term, [], f"Unknown system: {system}"

    try:
        results = await tool.search(term, max_results=max_results)
        return system, term, results, None
    except APIError as e:
        return system, term, [], str(e)
    except Exception as e:
        return system, term, [], f"Unexpected error: {e}"


async def execute_node(state: AgentState) -> dict[str, Any]:
    """
    LangGraph node: Execute searches in parallel across selected systems.

    Uses asyncio.Semaphore to limit concurrent API calls.
    """
    systems = state["selected_systems"]
    search_terms = state.get("search_terms", [state["query"]])
    existing_results = state.get("raw_results", {})
    api_calls = []

    # Build list of search tasks
    tasks = []
    for system in systems:
        for term in search_terms:
            tasks.append(execute_search(
                system,
                term,
                max_results=config.MAX_RESULTS_PER_SYSTEM,
            ))

    # Rate limit with semaphore
    semaphore = asyncio.Semaphore(5)

    async def limited_search(coro):
        async with semaphore:
            return await coro

    # Execute all searches in parallel
    results = await asyncio.gather(
        *[limited_search(t) for t in tasks],
        return_exceptions=True,
    )

    # Aggregate results by system
    new_results: dict[str, list[dict]] = {s: [] for s in systems}

    for result in results:
        if isinstance(result, Exception):
            api_calls.append({
                "system": "unknown",
                "term": "unknown",
                "status": "error",
                "error": str(result),
            })
            continue

        system, term, code_results, error = result

        api_calls.append({
            "system": system,
            "term": term,
            "status": "error" if error else "success",
            "count": len(code_results),
            "error": error,
        })

        if code_results:
            # Convert CodeResult to dict for storage
            for cr in code_results:
                new_results[system].append(cr.to_dict())

    # Merge with existing results (dedupe by code)
    merged_results: dict[str, list[dict]] = {}
    for system in systems:
        seen_codes: set[str] = set()
        merged: list[dict] = []

        # Add existing results first
        for r in existing_results.get(system, []):
            if r["code"] not in seen_codes:
                seen_codes.add(r["code"])
                merged.append(r)

        # Add new results
        for r in new_results.get(system, []):
            if r["code"] not in seen_codes:
                seen_codes.add(r["code"])
                merged.append(r)

        merged_results[system] = merged

    # Count total results
    total_results = sum(len(v) for v in merged_results.values())
    reasoning = f"Executed {len(api_calls)} API calls, found {total_results} total results"

    return {
        "raw_results": merged_results,
        "api_calls": api_calls,
        "reasoning_trace": [reasoning],
    }
