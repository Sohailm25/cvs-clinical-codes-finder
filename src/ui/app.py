# ABOUTME: Streamlit chat-style UI for Clinical Codes Finder.
# ABOUTME: Provides conversational interface with persistent session history.

import asyncio
import queue
import threading

import streamlit as st

from src.agent.graph import run_agent_streaming
from src.ui.session import (
    init_session_state,
    get_current_session,
    add_message,
)
from src.ui.sidebar import render_sidebar
from src.ui.chat import (
    render_user_message,
    render_assistant_message,
    render_results_compact,
    render_thinking_trace,
    render_api_calls,
    render_intent_scores,
)


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


def handle_query(query: str, settings: dict):
    """
    Handle a new user query with streaming and chat display.

    Args:
        query: The user's search query.
        settings: Current settings dict.
    """
    # Add user message to session
    add_message("user", query)

    # Display user message
    render_user_message(query)

    # Create assistant message with streaming status
    with st.chat_message("assistant", avatar="🏥"):
        status_placeholder = st.empty()

        try:
            # Run streaming search
            result = streaming_search(
                query,
                status_placeholder,
                multi_hop_enabled=settings.get("multi_hop_enabled", False),
            )

            # Check if clarification is needed
            if settings.get("clarification_enabled", True) and result.get("clarification_needed"):
                status_placeholder.empty()
                st.write("🤔 This query could apply to multiple coding systems. What are you looking for?")

                options = result.get("clarification_options", [])
                cols = st.columns(len(options) + 1)

                for i, opt in enumerate(options):
                    with cols[i]:
                        if st.button(opt["label"], key=f"clarify_{opt['intent']}_{query[:10]}"):
                            # Store clarification and rerun
                            st.session_state.pending_clarification = {
                                "query": query,
                                "intent": opt["intent"],
                            }
                            st.rerun()

                with cols[-1]:
                    if st.button("Search all", key=f"clarify_all_{query[:10]}", type="secondary"):
                        st.session_state.pending_clarification = {
                            "query": query,
                            "intent": "all",
                        }
                        st.rerun()

                # Don't save incomplete result
                return

            # Clear status
            status_placeholder.empty()

            # Display results
            summary = result.get("summary", "")
            if summary:
                st.markdown(summary)

            render_results_compact(result.get("consolidated_results", []))

            col1, col2 = st.columns(2)
            with col1:
                render_thinking_trace(result.get("reasoning_trace", []))
            with col2:
                render_api_calls(result.get("api_calls", []))

            render_intent_scores(result.get("intent_scores", {}))

            # Save result to session
            add_message("assistant", result)

        except Exception as e:
            status_placeholder.error(f"Search failed: {str(e)}")
            st.exception(e)


def handle_clarification(settings: dict):
    """Handle a pending clarification response."""
    clarification = st.session_state.pending_clarification
    st.session_state.pending_clarification = None

    query = clarification["query"]
    intent = clarification["intent"]

    # Add clarification as user message
    if intent != "all":
        intent_labels = {
            "diagnosis": "diagnosis codes",
            "laboratory": "lab test codes",
            "medication": "medication codes",
            "supplies": "supply/service codes",
            "units": "unit codes",
            "phenotype": "phenotype codes",
        }
        clarify_text = f"Search for {intent_labels.get(intent, intent)}"
        add_message("user", clarify_text)
        render_user_message(clarify_text)

    # Run search with clarification
    with st.chat_message("assistant", avatar="🏥"):
        status_placeholder = st.empty()

        try:
            result = streaming_search(
                query,
                status_placeholder,
                multi_hop_enabled=settings.get("multi_hop_enabled", False),
                user_clarification=intent,
            )

            status_placeholder.empty()

            summary = result.get("summary", "")
            if summary:
                st.markdown(summary)

            render_results_compact(result.get("consolidated_results", []))

            col1, col2 = st.columns(2)
            with col1:
                render_thinking_trace(result.get("reasoning_trace", []))
            with col2:
                render_api_calls(result.get("api_calls", []))

            render_intent_scores(result.get("intent_scores", {}))

            add_message("assistant", result)

        except Exception as e:
            status_placeholder.error(f"Search failed: {str(e)}")
            st.exception(e)


def main():
    """Main Streamlit application with chat-style interface."""
    st.set_page_config(
        page_title="Clinical Codes Finder",
        page_icon="🏥",
        layout="wide",
    )

    # Initialize session state
    init_session_state()

    # Render sidebar and get settings
    settings = render_sidebar()

    # Header
    st.title("🏥 Clinical Codes Finder")

    # Render existing chat messages
    session = get_current_session()
    for msg in session.get("messages", []):
        if msg["role"] == "user":
            render_user_message(msg["content"])
        else:
            render_assistant_message(msg["content"])

    # Handle pending clarification
    if st.session_state.get("pending_clarification"):
        handle_clarification(settings)

    # Chat input at bottom
    if query := st.chat_input("Type your clinical query (e.g., diabetes, glucose test, metformin 500 mg)"):
        handle_query(query, settings)
        st.rerun()


if __name__ == "__main__":
    main()
