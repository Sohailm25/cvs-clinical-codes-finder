# ABOUTME: Summary generation node for the clinical codes agent.
# ABOUTME: Produces plain-English explanation of findings.

from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from src.agent.state import AgentState
from src.tools.base import CodeResult
from src.config import config


SUMMARY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a clinical coding assistant. Provide brief, actionable guidance to help users choose the right code.

Query: {query}

Results by system:
{results_by_system}

Generate ONLY guidance and insights - do NOT list all the codes (they're shown separately).

FORMAT YOUR RESPONSE AS:

### Key Findings
- **Primary match**: **`CODE`** — brief why this matches, with the **key term** from the description bolded
- **Alternative**: **`CODE`** — when to use this instead (bold **key differentiator**)
- **Related**: Cross-system insight if relevant

### Notes
(ONLY if there are important caveats. Otherwise OMIT this section entirely.)

FORMATTING RULES:
- Make codes HIGHLY VISIBLE: always use **`CODE`** (bold + backticks together)
- Bold the **key terms** in descriptions that match the query (e.g., "**glucose** measurement")
- Be concise - 2-3 bullet points max
- Use em dash (—) after codes for cleaner separation
- Focus on DECISION GUIDANCE, not listing results"""),
    ("human", "Generate the guidance summary."),
])


SYSTEM_DESCRIPTIONS = {
    "ICD-10-CM": "Diagnosis Codes",
    "LOINC": "Lab Tests",
    "RxTerms": "Medications",
    "HCPCS": "Supplies & Services",
    "UCUM": "Units of Measure",
    "HPO": "Phenotypes & Symptoms",
}


def _confidence_label(confidence: float) -> str:
    """Convert confidence score to human-readable label."""
    if confidence > 0.6:
        return "High"
    elif confidence > 0.3:
        return "Medium"
    return "Low"


def format_results_for_summary(results: list[CodeResult]) -> str:
    """Format results by system for the summary prompt."""
    by_system: dict[str, list[CodeResult]] = {}

    for r in results:
        if r.system not in by_system:
            by_system[r.system] = []
        by_system[r.system].append(r)

    parts = []
    for system, system_results in by_system.items():
        desc = SYSTEM_DESCRIPTIONS.get(system, "Clinical Codes")
        part = f"\n{system} ({desc}):"
        for r in system_results[:5]:  # Show top 5 per system
            conf_label = _confidence_label(r.confidence)
            part += f"\n  - Code: {r.code}"
            part += f"\n    Display: {r.display}"
            part += f"\n    Confidence: {conf_label} ({r.confidence:.2f})"
        if len(system_results) > 5:
            part += f"\n  ... and {len(system_results) - 5} more results"
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
    """Generate a brief guidance summary without LLM."""
    if not results:
        return ""  # No summary needed if no results

    # Key finding (best match) - only guidance, not full listing
    parts = ["### Key Findings"]

    best = results[0]
    # Bold the query terms in the display
    display = _highlight_query_terms(best.display[:80], query)
    parts.append(f"- **Primary match**: **`{best.code}`** ({best.system}) — {display}")

    # Add alternative if there's a second result
    if len(results) > 1:
        alt = results[1]
        display = _highlight_query_terms(alt.display[:60], query)
        parts.append(f"- **Alternative**: **`{alt.code}`** ({alt.system}) — {display}")

    return "\n".join(parts)


def _highlight_query_terms(text: str, query: str) -> str:
    """Bold query terms found in text for visual highlighting."""
    import re
    # Extract meaningful words from query (skip short words)
    query_words = [w.lower() for w in query.split() if len(w) > 2]

    result = text
    for word in query_words:
        # Case-insensitive replacement, preserve original case
        pattern = re.compile(f'({re.escape(word)})', re.IGNORECASE)
        result = pattern.sub(r'**\1**', result)

    return result


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
