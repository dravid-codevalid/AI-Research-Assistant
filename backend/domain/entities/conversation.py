"""Conversation entity — core domain object representing a chat conversation."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Conversation:
    """Immutable domain entity representing a chat conversation.

    Attributes:
        id: Unique identifier for the conversation (UUID string).
        workspace_id: Workspace this conversation belongs to.
        created_by: User ID of the conversation creator.
        title: Human-readable title (auto-generated or user-set).
        created_at: ISO-8601 timestamp of creation, or None if unset.
        updated_at: ISO-8601 timestamp of last update, or None if unset.
    """

    id: str
    workspace_id: str | None = field(default=None)
    created_by: str | None = field(default=None)
    title: str = field(default="New Conversation")
    created_at: str | None = field(default=None)
    updated_at: str | None = field(default=None)
