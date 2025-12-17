# ABOUTME: Planning node for the clinical codes agent.
# ABOUTME: Determines search strategy and term refinements based on prior results.

from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from src.agent.state import AgentState
from src.config import config


REFINEMENT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a clinical terminology expert. Based on the search results so far, suggest refined search terms.

Current query: {query}
Systems being searched: {systems}
Current results: {result_summary}
Refinement strategy: {strategy}

Provide 1-3 refined search terms that might yield better results.
- For "broaden": suggest more general terms, synonyms, or remove modifiers
- For "narrow": suggest more specific terms, add qualifiers, or focus on key aspects

Respond with a JSON array of strings like: ["term1", "term2"]"""),
    ("human", "Suggest refined search terms."),
])


async def generate_refined_terms(
    query: str,
    systems: list[str],
    results_summary: str,
    strategy: str,
) -> list[str]:
    """Use LLM to generate refined search terms."""
    llm = ChatOpenAI(
        model=config.OPENAI_MODEL,
        temperature=0.3,
        api_key=config.OPENAI_API_KEY,
    )

    chain = REFINEMENT_PROMPT | llm

    try:
        response = await chain.ainvoke({
            "query": query,
            "systems": ", ".join(systems),
            "result_summary": results_summary,
            "strategy": strategy,
        })

        content = response.content.strip()

        import json
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        terms = json.loads(content)
        if isinstance(terms, list):
            return [str(t) for t in terms[:3]]
    except Exception:
        pass

    # Fallback: return original query
    return [query]


def summarize_results(raw_results: dict[str, list[dict]]) -> str:
    """Create a brief summary of current results for the LLM."""
    parts = []
    total = 0

    for system, results in raw_results.items():
        count = len(results)
        total += count
        if count > 0:
            sample = results[0].get("display", "")[:50]
            parts.append(f"{system}: {count} results (e.g., '{sample}...')")
        else:
            parts.append(f"{system}: 0 results")

    if not parts:
        return "No results yet"

    return f"Total: {total} results. " + "; ".join(parts)


async def plan_node(state: AgentState) -> dict[str, Any]:
    """
    LangGraph node: Plan search strategy and refine terms if needed.

    On first iteration, uses raw query.
    On subsequent iterations, may refine terms based on refinement_strategy.
    """
    iteration = state["iteration"]
    query = state["query"]
    systems = state["selected_systems"]
    strategy = state.get("refinement_strategy")
    raw_results = state.get("raw_results", {})

    reasoning_updates = []

    if iteration == 0:
        # First iteration: use original query
        search_terms = [query]
        reasoning_updates.append(
            f"Planning iteration {iteration + 1}: searching {', '.join(systems)} for '{query}'"
        )
    elif strategy:
        # Subsequent iteration with refinement needed
        results_summary = summarize_results(raw_results)
        new_terms = await generate_refined_terms(query, systems, results_summary, strategy)

        # Combine with existing terms (dedupe)
        existing = set(state.get("search_terms", []))
        search_terms = list(existing | set(new_terms))

        reasoning_updates.append(
            f"Planning iteration {iteration + 1}: {strategy} strategy, "
            f"added terms: {new_terms}"
        )
    else:
        # No refinement needed, keep existing terms
        search_terms = state.get("search_terms", [query])
        reasoning_updates.append(f"Planning iteration {iteration + 1}: continuing with existing terms")

    return {
        "search_terms": search_terms,
        "iteration": iteration + 1,
        "reasoning_trace": reasoning_updates,
    }
