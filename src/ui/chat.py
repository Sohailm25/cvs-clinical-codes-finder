# ABOUTME: Chat message rendering components for the chat-style UI.
# ABOUTME: Renders user and assistant messages with proper formatting.

import streamlit as st

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


def render_user_message(content: str):
    """
    Render a user query message in chat format.

    Args:
        content: The user's query text.
    """
    with st.chat_message("user"):
        st.write(content)


def render_results_compact(results: list) -> None:
    """
    Render code results in a compact format for chat messages.

    Args:
        results: List of CodeResult objects or dicts.
    """
    if not results:
        st.info("No results found for this query.")
        return

    # Convert dicts back to CodeResult-like access if needed
    def get_attr(r, key):
        if isinstance(r, dict):
            return r.get(key)
        return getattr(r, key, None)

    # Group by system
    by_system: dict[str, list] = {}
    for r in results:
        system = get_attr(r, "system") or "Unknown"
        if system not in by_system:
            by_system[system] = []
        by_system[system].append(r)

    # Render each system
    for system, system_results in by_system.items():
        with st.expander(f"**{system}** ({len(system_results)} results)", expanded=True):
            for r in system_results:
                code = get_attr(r, "code")
                display = get_attr(r, "display")
                confidence = get_attr(r, "confidence") or 0.0

                col1, col2 = st.columns([1, 4])
                with col1:
                    st.code(code)
                with col2:
                    st.write(f"**{display}**")
                    st.caption(f"Confidence: {get_confidence_badge(confidence)} ({confidence:.2f})")


def render_thinking_trace(reasoning_trace: list[str]):
    """Render the agent's reasoning trace."""
    if not reasoning_trace:
        return

    with st.expander("🧠 Agent Thinking", expanded=False):
        for i, trace in enumerate(reasoning_trace, 1):
            st.markdown(f"{i}. {trace}")


def render_api_calls(api_calls: list[dict]):
    """Render API call summary."""
    if not api_calls:
        return

    with st.expander("📡 API Calls", expanded=False):
        success_count = sum(1 for c in api_calls if c.get("status") == "success")
        error_count = len(api_calls) - success_count

        st.caption(f"Total: {len(api_calls)} calls ({success_count} successful, {error_count} errors)")

        for call in api_calls:
            status_icon = "✅" if call.get("status") == "success" else "❌"
            st.text(f"{status_icon} {call.get('system', 'Unknown')}: '{call.get('term', '')}' → {call.get('count', 0)} results")


def render_intent_scores(scores: dict):
    """Render intent classification scores."""
    if not scores:
        return

    with st.expander("🎯 Intent Classification", expanded=False):
        for intent, score in scores.items():
            if score > 0:
                st.progress(score, text=f"{intent}: {score:.2f}")


def render_assistant_message(result: dict):
    """
    Render an assistant response with full results.

    Args:
        result: The agent result dict containing summary, results, etc.
    """
    with st.chat_message("assistant", avatar="🏥"):
        # Summary
        summary = result.get("summary", "")
        if summary:
            st.markdown(summary)
        else:
            st.write("Search completed.")

        # Results
        results = result.get("consolidated_results", [])
        render_results_compact(results)

        # Details (all collapsed)
        col1, col2 = st.columns(2)
        with col1:
            render_thinking_trace(result.get("reasoning_trace", []))
        with col2:
            render_api_calls(result.get("api_calls", []))

        # Intent scores
        render_intent_scores(result.get("intent_scores", {}))


def render_clarification_request(options: list[dict], query: str) -> str | None:
    """
    Render a clarification request with option buttons.

    Args:
        options: List of {intent, label} dicts.
        query: The original query being clarified.

    Returns:
        The selected intent if a button was clicked, None otherwise.
    """
    with st.chat_message("assistant", avatar="🏥"):
        st.write("🤔 This query could apply to multiple coding systems. What are you looking for?")

        cols = st.columns(len(options))
        for i, opt in enumerate(options):
            with cols[i]:
                if st.button(opt["label"], key=f"clarify_{opt['intent']}_{query[:10]}"):
                    return opt["intent"]

        if st.button("Search all relevant systems", key=f"clarify_all_{query[:10]}", type="secondary"):
            return "all"

    return None


def render_streaming_status(status_text: str):
    """
    Render streaming status inside a chat message placeholder.

    Args:
        status_text: Status message to display.
    """
    st.info(status_text)
