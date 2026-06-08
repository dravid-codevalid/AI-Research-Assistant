"""UserWorkspace entity — association between a user and a workspace."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class UserWorkspace:
    """Immutable domain entity representing a user's membership in a workspace.

    Attributes:
        user_id: Foreign-key reference to the user.
        workspace_id: Foreign-key reference to the workspace.
        role: Membership role (e.g. ``'admin'``, ``'member'``).
        litellm_key: LiteLLM API key assigned to this user in this workspace.
    """

    user_id: str
    workspace_id: str
    role: str = field(default="member")
    litellm_key: str | None = field(default=None)
