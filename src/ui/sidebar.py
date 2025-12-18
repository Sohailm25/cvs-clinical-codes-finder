# ABOUTME: Sidebar components for the chat-style UI.
# ABOUTME: Renders settings, chat history, and new chat button.

import streamlit as st

from src.ui.session import (
    get_all_sessions,
    get_current_session,
    switch_session,
    create_new_session,
    delete_current_session,
)


def render_settings() -> dict:
    """
    Render settings toggles in the sidebar.

    Returns:
        Dict with current settings values.
    """
    st.header("⚙️ Settings")

    clarification_enabled = st.toggle(
        "Ask clarifying questions",
        value=st.session_state.settings.get("clarification_enabled", True),
        help="When query intent is ambiguous, show options to clarify",
        key="setting_clarification",
    )

    multi_hop_enabled = st.toggle(
        "Multi-hop reasoning",
        value=st.session_state.settings.get("multi_hop_enabled", False),
        help="Expand searches with clinically related codes",
        key="setting_multi_hop",
    )

    show_hierarchy = st.toggle(
        "Show code hierarchy",
        value=st.session_state.settings.get("show_hierarchy", True),
        help="Display parent codes for context",
        key="setting_hierarchy",
    )

    # Update session state
    st.session_state.settings = {
        "clarification_enabled": clarification_enabled,
        "multi_hop_enabled": multi_hop_enabled,
        "show_hierarchy": show_hierarchy,
    }

    return st.session_state.settings


def render_chat_history():
    """Render the list of chat sessions in the sidebar."""
    st.subheader("💬 Chat History")

    sessions = get_all_sessions()
    current_session = get_current_session()

    for session in sessions:
        is_current = session["id"] == current_session["id"]

        # Session name with indicator
        name = session.get("name", "New Chat")
        message_count = len(session.get("messages", []))

        # Use a container for each session
        col1, col2 = st.columns([5, 1])

        with col1:
            # Make the session name clickable
            label = f"{'● ' if is_current else '○ '}{name}"
            if st.button(
                label,
                key=f"session_{session['id']}",
                use_container_width=True,
                type="primary" if is_current else "secondary",
            ):
                if not is_current:
                    switch_session(session["id"])
                    st.rerun()

        with col2:
            # Delete button (only show if more than one session)
            if len(sessions) > 1:
                if st.button("🗑️", key=f"delete_{session['id']}", help="Delete this chat"):
                    if is_current:
                        delete_current_session()
                    else:
                        st.session_state.sessions = [
                            s for s in st.session_state.sessions if s["id"] != session["id"]
                        ]
                        from src.ui.storage import save_sessions
                        save_sessions(st.session_state.sessions)
                    st.rerun()


def render_new_chat_button():
    """Render the new chat button at the bottom of the sidebar."""
    st.divider()

    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        create_new_session()
        st.rerun()


def render_sidebar() -> dict:
    """
    Render the complete sidebar.

    Returns:
        Current settings dict.
    """
    with st.sidebar:
        settings = render_settings()
        st.divider()
        render_chat_history()
        render_new_chat_button()

        # Footer
        st.divider()
        st.caption(
            "Clinical Codes Finder searches 6 medical coding systems: "
            "ICD-10-CM, LOINC, RxTerms, HCPCS, UCUM, and HPO."
        )

    return settings
