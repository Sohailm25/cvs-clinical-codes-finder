# ABOUTME: Streamlit UI for Clinical Codes Finder.
# ABOUTME: Provides search interface with real-time "thinking" visualization.

import asyncio
import streamlit as st
from typing import Generator

from src.agent import run_agent
from src.agent.state import AgentState
from src.tools.base import CodeResult


def get_confidence_badge(confidence: float) -> str:
    """Get a colored badge based on confidence level."""
    if confidence >= 0.7:
        return "🟢 High"
    elif confidence >= 0.4:
        return "🟡 Medium"
    else:
        return "🔴 Low"


def format_results_by_system(results: list[CodeResult]) -> dict[str, list[CodeResult]]:
    """Group results by coding system."""
    by_system: dict[str, list[CodeResult]] = {}
    for r in results:
        if r.system not in by_system:
            by_system[r.system] = []
        by_system[r.system].append(r)
    return by_system


def display_results(results: list[CodeResult]):
    """Display results grouped by system."""
    if not results:
        st.warning("No results found. Try a different search term.")
        return

    by_system = format_results_by_system(results)

    for system, system_results in by_system.items():
        with st.expander(f"**{system}** ({len(system_results)} results)", expanded=True):
            for r in system_results:
                col1, col2 = st.columns([1, 4])
                with col1:
                    st.code(r.code)
                with col2:
                    st.write(f"**{r.display}**")
                    st.caption(f"Confidence: {get_confidence_badge(r.confidence)} ({r.confidence:.2f})")


def display_thinking(reasoning_trace: list[str]):
    """Display the agent's reasoning trace."""
    with st.expander("🧠 Agent Thinking Process", expanded=False):
        for i, trace in enumerate(reasoning_trace, 1):
            st.markdown(f"{i}. {trace}")


def display_api_calls(api_calls: list[dict]):
    """Display API call summary."""
    if not api_calls:
        return

    with st.expander("📡 API Calls Made", expanded=False):
        success_count = sum(1 for c in api_calls if c.get("status") == "success")
        error_count = len(api_calls) - success_count

        st.caption(f"Total: {len(api_calls)} calls ({success_count} successful, {error_count} errors)")

        for call in api_calls:
            status_icon = "✅" if call.get("status") == "success" else "❌"
            st.text(f"{status_icon} {call.get('system', 'Unknown')}: '{call.get('term', '')}' → {call.get('count', 0)} results")


async def run_search(query: str) -> AgentState:
    """Run the agent search asynchronously."""
    return await run_agent(query)


def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="Clinical Codes Finder",
        page_icon="🏥",
        layout="wide",
    )

    st.title("🏥 Clinical Codes Finder")
    st.markdown("""
    Enter a clinical term to find relevant codes across multiple medical coding systems:
    **ICD-10-CM** (diagnoses), **LOINC** (lab tests), **RxTerms** (drugs),
    **HCPCS** (supplies/services), **UCUM** (units), **HPO** (phenotypes)
    """)

    # Search input
    col1, col2 = st.columns([4, 1])
    with col1:
        query = st.text_input(
            "Search term",
            placeholder="e.g., diabetes, glucose test, metformin 500 mg, wheelchair",
            label_visibility="collapsed",
        )
    with col2:
        search_button = st.button("🔍 Search", type="primary", use_container_width=True)

    # Example queries
    st.caption("**Try these examples:** diabetes | glucose test | metformin 500 mg | wheelchair | mg/dL | ataxia")

    st.divider()

    # Run search
    if search_button and query:
        with st.spinner("🤔 Analyzing query and searching databases..."):
            try:
                # Run the async agent
                result = asyncio.run(run_search(query))

                # Display summary
                st.success("Search complete!")
                st.markdown(f"### Summary\n{result['summary']}")

                # Display results
                st.markdown("### Results")
                display_results(result.get("consolidated_results", []))

                # Display thinking process
                st.markdown("### Details")
                col1, col2 = st.columns(2)
                with col1:
                    display_thinking(result.get("reasoning_trace", []))
                with col2:
                    display_api_calls(result.get("api_calls", []))

                # Show intent scores
                with st.expander("🎯 Intent Classification", expanded=False):
                    scores = result.get("intent_scores", {})
                    for intent, score in scores.items():
                        if score > 0:
                            st.progress(score, text=f"{intent}: {score:.2f}")

            except Exception as e:
                st.error(f"Search failed: {str(e)}")
                st.exception(e)

    elif search_button and not query:
        st.warning("Please enter a search term.")

    # Footer
    st.divider()
    st.caption("Powered by Clinical Tables API (NIH NLM) • Built with LangGraph & Streamlit")


if __name__ == "__main__":
    main()
