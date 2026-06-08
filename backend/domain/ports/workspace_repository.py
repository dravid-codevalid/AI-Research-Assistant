"""Workspace repository port — abstract interface for workspace persistence."""

from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.user_workspace import UserWorkspace
from domain.entities.workspace import Workspace


class IWorkspaceRepository(ABC):
    """Abstract interface for workspace data access.

    Concrete implementations (e.g. SQLAlchemy adapter) must satisfy
    this contract so the domain layer stays decoupled from infrastructure.
    """

    # ── Workspace CRUD ──────────────────────────────────────────────

    @abstractmethod
    async def create(self, workspace: Workspace) -> Workspace:
        """Persist a new workspace and return the stored entity."""

    @abstractmethod
    async def get_by_id(self, workspace_id: str) -> Workspace | None:
        """Return a workspace by ID, or ``None`` if not found."""

    @abstractmethod
    async def list_all(self) -> list[Workspace]:
        """Return every workspace in the system."""

    # ── Membership management ───────────────────────────────────────

    @abstractmethod
    async def add_member(self, membership: UserWorkspace) -> UserWorkspace:
        """Add a user to a workspace."""

    @abstractmethod
    async def get_members(self, workspace_id: str) -> list[UserWorkspace]:
        """Return all membership records for a workspace."""

    @abstractmethod
    async def get_user_workspaces(self, user_id: str) -> list[UserWorkspace]:
        """Return all workspace memberships for a user."""

    @abstractmethod
    async def get_membership(
        self, user_id: str, workspace_id: str
    ) -> UserWorkspace | None:
        """Return a single membership record, or ``None`` if not found."""
