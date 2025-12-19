# ABOUTME: File-based data persistence layer for Chainlit.
# ABOUTME: Stores threads and messages in a local JSON file for demo purposes.

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from chainlit.data import BaseDataLayer
from chainlit.types import (
    Feedback,
    PageInfo,
    PaginatedResponse,
    Pagination,
    ThreadDict,
    ThreadFilter,
)
from chainlit.user import User, PersistedUser
from chainlit.step import StepDict
from chainlit.element import ElementDict


DATA_DIR = Path.home() / ".clinical_codes_finder"
THREADS_FILE = DATA_DIR / "threads.json"


def _ensure_data_dir():
    """Ensure the data directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_data() -> dict:
    """Load data from the JSON file."""
    _ensure_data_dir()
    if THREADS_FILE.exists():
        try:
            with open(THREADS_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"users": {}, "threads": {}, "steps": {}, "elements": {}}
    return {"users": {}, "threads": {}, "steps": {}, "elements": {}}


def _save_data(data: dict):
    """Save data to the JSON file."""
    _ensure_data_dir()
    with open(THREADS_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)


class FileDataLayer(BaseDataLayer):
    """Simple file-based data layer for demo purposes."""

    async def get_user(self, identifier: str) -> Optional[PersistedUser]:
        """Get a user by identifier."""
        data = _load_data()
        user_data = data["users"].get(identifier)
        if user_data:
            return PersistedUser(
                id=user_data["id"],
                identifier=user_data["identifier"],
                metadata=user_data.get("metadata", {}),
                createdAt=user_data.get("createdAt", datetime.now(timezone.utc).isoformat()),
            )
        return None

    async def create_user(self, user: User) -> Optional[PersistedUser]:
        """Create a new user."""
        data = _load_data()
        now = datetime.now(timezone.utc).isoformat()
        user_data = {
            "id": user.identifier,
            "identifier": user.identifier,
            "metadata": user.metadata or {},
            "createdAt": now,
        }
        data["users"][user.identifier] = user_data
        _save_data(data)
        return PersistedUser(
            id=user.identifier,
            identifier=user.identifier,
            metadata=user.metadata or {},
            createdAt=now,
        )

    async def get_thread(self, thread_id: str) -> Optional[ThreadDict]:
        """Get a thread by ID."""
        data = _load_data()
        thread = data["threads"].get(thread_id)
        if thread:
            # Attach steps to the thread
            thread["steps"] = [
                s for s in data["steps"].values()
                if s.get("threadId") == thread_id
            ]
            return thread
        return None

    async def get_thread_author(self, thread_id: str) -> str:
        """Get the author of a thread."""
        data = _load_data()
        thread = data["threads"].get(thread_id)
        if thread:
            return thread.get("userId", "anonymous")
        return "anonymous"

    async def list_threads(
        self,
        pagination: Pagination,
        filters: ThreadFilter,
    ) -> PaginatedResponse[ThreadDict]:
        """List threads with pagination."""
        data = _load_data()
        threads = list(data["threads"].values())

        # Filter by user if specified
        if filters.userId:
            threads = [t for t in threads if t.get("userId") == filters.userId]

        # Sort by createdAt descending (newest first)
        threads.sort(key=lambda t: t.get("createdAt", ""), reverse=True)

        # Apply pagination
        start = 0
        if pagination.cursor:
            # Find the position after the cursor
            for i, t in enumerate(threads):
                if t["id"] == pagination.cursor:
                    start = i + 1
                    break

        end = start + pagination.first
        page_threads = threads[start:end]

        # Attach steps to each thread
        for thread in page_threads:
            thread["steps"] = [
                s for s in data["steps"].values()
                if s.get("threadId") == thread["id"]
            ]

        has_next = end < len(threads)
        end_cursor = page_threads[-1]["id"] if page_threads else None

        start_cursor = page_threads[0]["id"] if page_threads else None

        return PaginatedResponse(
            data=page_threads,
            pageInfo=PageInfo(
                hasNextPage=has_next,
                startCursor=start_cursor,
                endCursor=end_cursor,
            ),
        )

    async def update_thread(
        self,
        thread_id: str,
        name: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[dict] = None,
        tags: Optional[list[str]] = None,
    ):
        """Update a thread."""
        data = _load_data()
        if thread_id not in data["threads"]:
            # Create new thread
            data["threads"][thread_id] = {
                "id": thread_id,
                "createdAt": datetime.now(timezone.utc).isoformat(),
                "name": name or "New Chat",
                "userId": user_id,
                "metadata": metadata or {},
                "tags": tags or [],
            }
        else:
            # Update existing thread
            thread = data["threads"][thread_id]
            if name is not None:
                thread["name"] = name
            if user_id is not None:
                thread["userId"] = user_id
            if metadata is not None:
                thread["metadata"] = metadata
            if tags is not None:
                thread["tags"] = tags
        _save_data(data)

    async def delete_thread(self, thread_id: str):
        """Delete a thread and its associated data."""
        data = _load_data()
        if thread_id in data["threads"]:
            del data["threads"][thread_id]
        # Also delete associated steps
        data["steps"] = {
            k: v for k, v in data["steps"].items()
            if v.get("threadId") != thread_id
        }
        # Also delete associated elements
        data["elements"] = {
            k: v for k, v in data["elements"].items()
            if v.get("threadId") != thread_id
        }
        _save_data(data)

    async def create_step(self, step_dict: StepDict):
        """Create a step."""
        data = _load_data()
        step_id = step_dict.get("id")
        if step_id:
            data["steps"][step_id] = step_dict
            _save_data(data)

    async def update_step(self, step_dict: StepDict):
        """Update a step."""
        data = _load_data()
        step_id = step_dict.get("id")
        if step_id:
            if step_id in data["steps"]:
                data["steps"][step_id].update(step_dict)
            else:
                data["steps"][step_id] = step_dict
            _save_data(data)

    async def delete_step(self, step_id: str):
        """Delete a step."""
        data = _load_data()
        if step_id in data["steps"]:
            del data["steps"][step_id]
            _save_data(data)

    async def create_element(self, element_dict: ElementDict):
        """Create an element."""
        data = _load_data()
        element_id = element_dict.get("id")
        if element_id:
            data["elements"][element_id] = element_dict
            _save_data(data)

    async def get_element(
        self,
        thread_id: str,
        element_id: str,
    ) -> Optional[ElementDict]:
        """Get an element by ID."""
        data = _load_data()
        element = data["elements"].get(element_id)
        if element and element.get("threadId") == thread_id:
            return element
        return None

    async def delete_element(self, element_id: str, thread_id: Optional[str] = None):
        """Delete an element."""
        data = _load_data()
        if element_id in data["elements"]:
            del data["elements"][element_id]
            _save_data(data)

    async def upsert_feedback(self, feedback: Feedback) -> str:
        """Upsert feedback (not implemented for file-based storage)."""
        return feedback.id or "feedback-not-stored"

    async def delete_feedback(self, feedback_id: str) -> bool:
        """Delete feedback (not implemented for file-based storage)."""
        return True

    async def build_debug_url(self) -> str:
        """Build debug URL (not applicable for file-based storage)."""
        return ""

    async def close(self):
        """Clean up resources (nothing to close for file-based storage)."""
        pass
