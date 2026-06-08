"""SQLAlchemy workspace repository adapter — concrete implementation of IWorkspaceRepository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.user_workspace import UserWorkspace
from domain.entities.workspace import Workspace
from domain.ports.workspace_repository import IWorkspaceRepository
from infrastructure.models import UserWorkspaceModel, WorkspaceModel


class SqlAlchemyWorkspaceRepository(IWorkspaceRepository):
    """Concrete workspace repository backed by an async SQLAlchemy session.

    Each public method operates within the caller-supplied session,
    keeping transaction control in the hands of the use-case layer.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _to_entity(model: WorkspaceModel) -> Workspace:
        """Map an ORM model instance to a domain entity."""
        return Workspace(
            id=model.id,
            name=model.name,
            created_at=model.created_at,
            litellm_team_id=model.litellm_team_id,
        )

    @staticmethod
    def _membership_to_entity(model: UserWorkspaceModel) -> UserWorkspace:
        """Map an ORM join-model instance to a domain entity."""
        return UserWorkspace(
            user_id=model.user_id,
            workspace_id=model.workspace_id,
            role=model.role,
            litellm_key=model.litellm_key,
        )

    # ── Workspace CRUD ──────────────────────────────────────────────

    async def create(self, workspace: Workspace) -> Workspace:
        """Persist a new workspace and return the stored entity."""
        model = WorkspaceModel(
            id=workspace.id,
            name=workspace.name,
            litellm_team_id=workspace.litellm_team_id,
            **({
                "created_at": workspace.created_at
            } if workspace.created_at else {}),
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def get_by_id(self, workspace_id: str) -> Workspace | None:
        """Return a workspace by ID, or ``None`` if not found."""
        result = await self._session.execute(
            select(WorkspaceModel).where(WorkspaceModel.id == workspace_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_all(self) -> list[Workspace]:
        """Return every workspace in the system."""
        result = await self._session.execute(select(WorkspaceModel))
        return [self._to_entity(m) for m in result.scalars().all()]

    # ── Membership management ───────────────────────────────────────

    async def add_member(self, membership: UserWorkspace) -> UserWorkspace:
        """Add a user to a workspace.

        Accepts a UserWorkspace domain entity containing user_id, workspace_id,
        role, and optional litellm_key.
        """
        model = UserWorkspaceModel(
            user_id=membership.user_id,
            workspace_id=membership.workspace_id,
            role=membership.role,
            litellm_key=membership.litellm_key,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._membership_to_entity(model)

    async def get_members(self, workspace_id: str) -> list[UserWorkspace]:
        """Return all membership records for a workspace."""
        result = await self._session.execute(
            select(UserWorkspaceModel).where(
                UserWorkspaceModel.workspace_id == workspace_id
            )
        )
        return [self._membership_to_entity(m) for m in result.scalars().all()]

    async def get_user_workspaces(self, user_id: str) -> list[UserWorkspace]:
        """Return all workspace memberships for a user."""
        result = await self._session.execute(
            select(UserWorkspaceModel).where(
                UserWorkspaceModel.user_id == user_id
            )
        )
        return [self._membership_to_entity(m) for m in result.scalars().all()]

    async def get_membership(
        self, user_id: str, workspace_id: str
    ) -> UserWorkspace | None:
        """Return a single membership record, or ``None`` if not found."""
        result = await self._session.execute(
            select(UserWorkspaceModel).where(
                UserWorkspaceModel.user_id == user_id,
                UserWorkspaceModel.workspace_id == workspace_id,
            )
        )
        model = result.scalar_one_or_none()
        return self._membership_to_entity(model) if model else None
