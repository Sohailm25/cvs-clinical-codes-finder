# ABOUTME: Persistent storage for chat history using local JSON files.
# ABOUTME: Saves and loads session data to ~/.clinical_codes_finder/chat_history.json.

import json
from pathlib import Path
from typing import Any

HISTORY_DIR = Path.home() / ".clinical_codes_finder"
HISTORY_FILE = HISTORY_DIR / "chat_history.json"


def _ensure_dir():
    """Ensure the storage directory exists."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def load_sessions() -> list[dict]:
    """
    Load all chat sessions from disk.

    Returns:
        List of session dicts, empty list if file doesn't exist.
    """
    if not HISTORY_FILE.exists():
        return []

    try:
        content = HISTORY_FILE.read_text()
        return json.loads(content)
    except (json.JSONDecodeError, IOError):
        return []


def save_sessions(sessions: list[dict]):
    """
    Save all chat sessions to disk.

    Args:
        sessions: List of session dicts to persist.
    """
    _ensure_dir()

    # Custom serializer for non-JSON types
    def default_serializer(obj: Any) -> Any:
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        return str(obj)

    content = json.dumps(sessions, indent=2, default=default_serializer)
    HISTORY_FILE.write_text(content)


def delete_session(sessions: list[dict], session_id: str) -> list[dict]:
    """
    Delete a specific session by ID.

    Args:
        sessions: Current list of sessions.
        session_id: ID of session to delete.

    Returns:
        Updated sessions list without the deleted session.
    """
    updated = [s for s in sessions if s.get("id") != session_id]
    save_sessions(updated)
    return updated


def clear_all_sessions():
    """Delete all chat history."""
    if HISTORY_FILE.exists():
        HISTORY_FILE.unlink()
