"""Workspace entity — core domain object representing a collaborative workspace."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Workspace:
    """Immutable domain entity representing a research workspace.

    Attributes:
        id: Unique identifier for the workspace (UUID string).
        name: Human-readable workspace name.
        created_at: ISO-8601 timestamp of workspace creation, or None if unset.
        litellm_team_id: Corresponding LiteLLM Team ID for spend tracking.
    """

    id: str
    name: str
    created_at: str | None = field(default=None)
    litellm_team_id: str | None = field(default=None)
