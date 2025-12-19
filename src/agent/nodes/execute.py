# ABOUTME: Execution node for the clinical codes agent.
# ABOUTME: Runs parallel API calls to selected coding systems.

import asyncio
import logging
from typing import Any

from src.agent.state import AgentState
from src.tools import ICD10Tool, LOINCTool, RxTermsTool, HCPCSTool, UCUMTool, HPOTool
from src.tools.base import ClinicalTablesClient, CodeResult, APIError
from src.services.cache import APIResponseCache
from src.services.http import HTTPClientManager
from src.config import config

logger = logging.getLogger(__name__)

# Shared infrastructure for all tools
_cache: APIResponseCache | None = None
_http_manager: HTTPClientManager | None = None
_tools: dict | None = None


def _get_shared_client() -> ClinicalTablesClient:
    """Get a ClinicalTablesClient with shared cache and HTTP pooling."""
    global _cache, _http_manager

    if config.CACHE_ENABLED and _cache is None:
        _cache = APIResponseCache(default_ttl=config.CACHE_TTL)
        logger.info("API response caching enabled")

    if _http_manager is None:
        _http_manager = HTTPClientManager.get_instance_sync()
        logger.info("HTTP connection pooling enabled")

    return ClinicalTablesClient(
        timeout=config.API_TIMEOUT,
        cache=_cache if config.CACHE_ENABLED else None,
        http_manager=_http_manager,
    )


def _get_tools() -> dict:
    """Get tool instances with shared caching client."""
    global _tools

    if _tools is None:
        client = _get_shared_client()
        _tools = {
            "ICD-10-CM": ICD10Tool(client=client),
            "LOINC": LOINCTool(client=client),
            "RxTerms": RxTermsTool(client=client),
            "HCPCS": HCPCSTool(client=client),
            "UCUM": UCUMTool(client=client),
            "HPO": HPOTool(client=client),
        }
        logger.info("Tools initialized with shared caching client")

    return _tools


def _safe_error_message(e: Exception) -> str:
    """Return a sanitized error message for display to users."""
    if isinstance(e, APIError):
        return "Clinical Tables API is temporarily unavailable"
    if isinstance(e, asyncio.TimeoutError):
        return "Request timed out"
    # Log the full error for debugging, but return generic message to user
    logger.error(f"Unexpected error in execute_search: {type(e).__name__}: {e}")
    return "An error occurred processing the request"


async def execute_search(
    system: str,
    term: str,
    max_results: int = 10,
) -> tuple[str, str, list[CodeResult], str | None]:
    """
    Execute a single search and return results.

    Returns: (system, term, results, error_message)
    """
    tools = _get_tools()
    tool = tools.get(system)
    if not tool:
        return system, term, [], f"Unknown system: {system}"

    try:
        results = await tool.search(term, max_results=max_results)
        return system, term, results, None
    except Exception as e:
        return system, term, [], _safe_error_message(e)


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
                "error": _safe_error_message(result),
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
            # Convert CodeResult to dict for storage, tracking which term found it
            for cr in code_results:
                result_dict = cr.to_dict()
                result_dict["search_term"] = term  # Track which term found this result
                new_results[system].append(result_dict)

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
