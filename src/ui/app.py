# ABOUTME: Streamlit UI for Clinical Codes Finder.
# ABOUTME: Provides search interface with real-time "thinking" visualization.

import asyncio
import queue
import threading
import time
from typing import Any

import streamlit as st

from src.agent.graph import run_agent_streaming, compile_graph
from src.agent.state import AgentState, create_initial_state
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


def run_async_in_thread(
    query: str,
    result_queue: queue.Queue,
    *,
    multi_hop_enabled: bool = False,
    user_clarification: str | None = None,
):
    """Run async streaming in a new event loop in a separate thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        async def collect():
            async for event in run_agent_streaming(
                query,
                multi_hop_enabled=multi_hop_enabled,
                user_clarification=user_clarification,
            ):
                result_queue.put(event)
            result_queue.put(None)  # Sentinel to signal completion

        loop.run_until_complete(collect())
    finally:
        loop.close()


NODE_STATUS_MESSAGES = {
    "classify": ("🎯", "Classifying query intent..."),
    "plan": ("📋", "Planning search strategy..."),
    "multi_hop": ("🔗", "Finding related clinical codes..."),
    "execute": ("🔍", "Searching APIs..."),
    "reflect": ("🤔", "Analyzing results..."),
    "consolidate": ("📊", "Consolidating findings..."),
    "summarize": ("✅", "Generating summary..."),
}


def streaming_search(
    query: str,
    status_placeholder,
    *,
    multi_hop_enabled: bool = False,
    user_clarification: str | None = None,
) -> dict:
    """Search with streaming updates displayed in real-time."""
    result_queue: queue.Queue = queue.Queue()

    # Start async execution in background thread
    thread = threading.Thread(
        target=run_async_in_thread,
        args=(query, result_queue),
        kwargs={
            "multi_hop_enabled": multi_hop_enabled,
            "user_clarification": user_clarification,
        },
        daemon=True,
    )
    thread.start()

    # Track final state as we receive updates
    final_state: dict = {}
    completed_nodes: list[str] = []

    while True:
        try:
            event = result_queue.get(timeout=60)  # 60s timeout
        except queue.Empty:
            status_placeholder.error("Search timed out")
            break

        if event is None:
            # Sentinel received - all done
            break

        node = event["node"]
        state_update = event["state"]

        # Merge state update into final state
        final_state.update(state_update)
        completed_nodes.append(node)

        # Update status display
        icon, message = NODE_STATUS_MESSAGES.get(node, ("⏳", f"Processing {node}..."))

        # Show additional context based on node
        if node == "plan":
            systems = state_update.get("selected_systems", [])
            if systems:
                message = f"Planning search: {', '.join(systems)}"
        elif node == "execute":
            calls = state_update.get("api_calls", [])
            if calls:
                message = f"Searching APIs ({len(calls)} calls)..."
        elif node == "multi_hop":
            related = state_update.get("related_terms", [])
            if related:
                message = f"Expanding with {len(related)} related terms..."

        status_placeholder.info(f"{icon} {message}")

    thread.join(timeout=5)
    return final_state


def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="Clinical Codes Finder",
        page_icon="🏥",
        layout="wide",
    )

    # Initialize session state
    if "clarification_choice" not in st.session_state:
        st.session_state.clarification_choice = None
    if "pending_query" not in st.session_state:
        st.session_state.pending_query = None
    if "last_result" not in st.session_state:
        st.session_state.last_result = None

    # Settings sidebar
    with st.sidebar:
        st.header("⚙️ Settings")

        clarification_enabled = st.toggle(
            "Ask clarifying questions",
            value=True,
            help="When query intent is ambiguous, show options to clarify"
        )

        multi_hop_enabled = st.toggle(
            "Multi-hop reasoning",
            value=False,
            help="Expand searches with clinically related codes"
        )

        show_hierarchy = st.toggle(
            "Show code hierarchy",
            value=True,
            help="Display parent codes for context"
        )

        st.divider()
        st.caption("**About**")
        st.caption(
            "Clinical Codes Finder uses AI to search 6 medical coding systems: "
            "ICD-10-CM, LOINC, RxTerms, HCPCS, UCUM, and HPO."
        )

    # Main content
    st.title("🏥 Clinical Codes Finder")
    st.markdown("""
    Enter a clinical term to find relevant codes across multiple medical coding systems:
    **ICD-10-CM** (diagnoses), **LOINC** (lab tests), **RxTerms** (drugs),
    **HCPCS** (supplies/services), **UCUM** (units), **HPO** (phenotypes)
    """)

    # Search input (wrapped in form so Enter submits)
    with st.form("search_form", clear_on_submit=False):
        col1, col2 = st.columns([4, 1])
        with col1:
            query = st.text_input(
                "Search term",
                placeholder="e.g., diabetes, glucose test, metformin 500 mg, wheelchair",
                label_visibility="collapsed",
            )
        with col2:
            search_button = st.form_submit_button("🔍 Search", type="primary", use_container_width=True)

    # Example queries
    st.caption("**Try these examples:** diabetes | glucose test | metformin 500 mg | wheelchair | mg/dL | ataxia")

    st.divider()

    # Handle clarification choice if pending
    if st.session_state.clarification_choice:
        query = st.session_state.pending_query
        user_clarification = st.session_state.clarification_choice
        st.session_state.clarification_choice = None
        st.session_state.pending_query = None

        # Run search with clarification
        status_placeholder = st.empty()
        try:
            result = streaming_search(
                query,
                status_placeholder,
                multi_hop_enabled=multi_hop_enabled,
                user_clarification=user_clarification,
            )
            status_placeholder.success("✅ Search complete!")
            st.session_state.last_result = result
        except Exception as e:
            status_placeholder.error(f"Search failed: {str(e)}")
            st.exception(e)
            return

    # Run search on button click
    elif search_button and query:
        status_placeholder = st.empty()

        try:
            result = streaming_search(
                query,
                status_placeholder,
                multi_hop_enabled=multi_hop_enabled,
            )

            # Check if clarification is needed
            if clarification_enabled and result.get("clarification_needed"):
                status_placeholder.empty()
                st.warning("🤔 This query could apply to multiple coding systems. Please clarify:")

                options = result.get("clarification_options", [])
                cols = st.columns(len(options))
                for i, opt in enumerate(options):
                    with cols[i]:
                        if st.button(opt["label"], key=f"clarify_{opt['intent']}"):
                            st.session_state.clarification_choice = opt["intent"]
                            st.session_state.pending_query = query
                            st.rerun()

                # Option to proceed anyway
                if st.button("Search all relevant systems", type="secondary"):
                    # Re-run without clarification
                    result = streaming_search(
                        query,
                        status_placeholder,
                        multi_hop_enabled=multi_hop_enabled,
                        user_clarification="all",
                    )
                    st.session_state.last_result = result
                else:
                    return  # Wait for user choice
            else:
                status_placeholder.success("✅ Search complete!")
                st.session_state.last_result = result

        except Exception as e:
            status_placeholder.error(f"Search failed: {str(e)}")
            st.exception(e)
            return

    elif search_button and not query:
        st.warning("Please enter a search term.")
        return

    # Display results if available
    result = st.session_state.last_result
    if result:
        # Display summary
        st.markdown(f"### Summary\n{result.get('summary', 'No summary available.')}")

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

    # Footer
    st.divider()
    st.caption("Powered by Clinical Tables API (NIH NLM) • Built with LangGraph & Streamlit")


if __name__ == "__main__":
    main()
