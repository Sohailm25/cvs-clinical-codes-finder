# ABOUTME: Session management for chat-style interface.
# ABOUTME: Handles session creation, switching, and message management.

import time
import uuid
from typing import Any

import streamlit as st

from src.ui.storage import load_sessions, save_sessions


def init_session_state():
    """
    Initialize Streamlit session state with default values.

    Called once at app startup. Loads persistent history from disk.
    """
    if "initialized" in st.session_state:
        return

    # Load persistent sessions
    sessions = load_sessions()

    # If no sessions exist, create a default one
    if not sessions:
        default_session = _create_session_dict()
        sessions = [default_session]
        save_sessions(sessions)

    st.session_state.sessions = sessions
    st.session_state.current_session_id = sessions[0]["id"]

    # Settings with defaults
    if "settings" not in st.session_state:
        st.session_state.settings = {
            "clarification_enabled": True,
            "multi_hop_enabled": False,
            "show_hierarchy": True,
        }

    # Track clarification state
    if "pending_clarification" not in st.session_state:
        st.session_state.pending_clarification = None

    st.session_state.initialized = True


def _create_session_dict(name: str | None = None) -> dict:
    """Create a new session dict structure."""
    return {
        "id": str(uuid.uuid4()),
        "name": name or "New Chat",
        "created_at": time.time(),
        "messages": [],
    }


def create_new_session() -> str:
    """
    Create a new chat session and switch to it.

    Returns:
        ID of the newly created session.
    """
    new_session = _create_session_dict()
    st.session_state.sessions.insert(0, new_session)
    st.session_state.current_session_id = new_session["id"]
    save_sessions(st.session_state.sessions)
    return new_session["id"]


def get_current_session() -> dict:
    """
    Get the current active session.

    Returns:
        The current session dict.
    """
    for session in st.session_state.sessions:
        if session["id"] == st.session_state.current_session_id:
            return session

    # Fallback to first session
    if st.session_state.sessions:
        st.session_state.current_session_id = st.session_state.sessions[0]["id"]
        return st.session_state.sessions[0]

    # Create new if none exist
    create_new_session()
    return st.session_state.sessions[0]


def switch_session(session_id: str):
    """
    Switch to a different session.

    Args:
        session_id: ID of the session to switch to.
    """
    st.session_state.current_session_id = session_id
    st.session_state.pending_clarification = None


def add_message(role: str, content: Any):
    """
    Add a message to the current session.

    Args:
        role: Either "user" or "assistant".
        content: Message content (string for user, dict for assistant).
    """
    session = get_current_session()

    message = {
        "role": role,
        "content": content,
        "timestamp": time.time(),
    }

    session["messages"].append(message)

    # Auto-name session from first user message
    if role == "user" and len(session["messages"]) == 1:
        # Truncate to 30 chars
        name = content[:30] + "..." if len(content) > 30 else content
        session["name"] = name

    # Persist to disk
    save_sessions(st.session_state.sessions)


def delete_current_session():
    """Delete the current session and switch to another."""
    current_id = st.session_state.current_session_id
    sessions = st.session_state.sessions

    # Remove current session
    sessions = [s for s in sessions if s["id"] != current_id]

    # If no sessions left, create a new one
    if not sessions:
        sessions = [_create_session_dict()]

    st.session_state.sessions = sessions
    st.session_state.current_session_id = sessions[0]["id"]
    save_sessions(sessions)


def get_all_sessions() -> list[dict]:
    """
    Get all sessions sorted by creation time (newest first).

    Returns:
        List of session dicts.
    """
    return sorted(
        st.session_state.sessions,
        key=lambda s: s.get("created_at", 0),
        reverse=True,
    )
