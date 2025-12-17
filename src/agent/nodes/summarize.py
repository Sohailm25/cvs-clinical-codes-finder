# ABOUTME: Summary generation node for the clinical codes agent.
# ABOUTME: Produces plain-English explanation of findings.

from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from src.agent.state import AgentState
from src.tools.base import CodeResult
from src.config import config


SUMMARY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a clinical coding assistant. Generate a concise summary of the code search results.

Query: {query}

Results by system:
{results_by_system}

Write a 2-3 sentence plain-English summary that:
1. States what was found (e.g., "Found 5 diagnosis codes for diabetes")
2. Highlights the most relevant results
3. Notes any important caveats (e.g., multiple formulations, ambiguous matches)

Keep the tone professional but accessible to non-technical healthcare administrators."""),
    ("human", "Generate the summary."),
])


def format_results_for_summary(results: list[CodeResult]) -> str:
    """Format results by system for the summary prompt."""
    by_system: dict[str, list[CodeResult]] = {}

    for r in results:
        if r.system not in by_system:
            by_system[r.system] = []
        by_system[r.system].append(r)

    parts = []
    for system, system_results in by_system.items():
        part = f"\n{system}:"
        for r in system_results[:3]:  # Show top 3 per system
            conf_label = "high" if r.confidence > 0.6 else "medium" if r.confidence > 0.3 else "low"
            part += f"\n  - {r.code}: {r.display} (confidence: {conf_label})"
        if len(system_results) > 3:
            part += f"\n  ... and {len(system_results) - 3} more"
        parts.append(part)

    return "\n".join(parts) if parts else "No results found"


async def generate_summary_with_llm(query: str, results: list[CodeResult]) -> str:
    """Use LLM to generate a natural language summary."""
    llm = ChatOpenAI(
        model=config.OPENAI_MODEL,
        temperature=0.3,
        api_key=config.OPENAI_API_KEY,
    )

    chain = SUMMARY_PROMPT | llm

    try:
        response = await chain.ainvoke({
            "query": query,
            "results_by_system": format_results_for_summary(results),
        })
        return response.content.strip()
    except Exception as e:
        # Fallback to simple summary
        return generate_fallback_summary(query, results)


def generate_fallback_summary(query: str, results: list[CodeResult]) -> str:
    """Generate a simple summary without LLM."""
    if not results:
        return f"No clinical codes found for '{query}'."

    # Count by system
    by_system: dict[str, int] = {}
    for r in results:
        by_system[r.system] = by_system.get(r.system, 0) + 1

    system_parts = [f"{count} {system} code(s)" for system, count in by_system.items()]

    if len(results) == 1:
        r = results[0]
        return f"Found 1 result for '{query}': {r.system} code {r.code} ({r.display})."

    return f"Found {len(results)} results for '{query}': {', '.join(system_parts)}."


async def summarize_node(state: AgentState) -> dict[str, Any]:
    """
    LangGraph node: Generate plain-English summary of results.
    """
    query = state["query"]
    results = state.get("consolidated_results", [])

    if results:
        summary = await generate_summary_with_llm(query, results)
    else:
        summary = f"No clinical codes found matching '{query}'. Try a different search term or check spelling."

    return {
        "summary": summary,
        "reasoning_trace": [f"Generated summary for {len(results)} results"],
    }
