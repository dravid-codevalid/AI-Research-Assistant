"""Workspaces route — CRUD endpoints for workspace and membership management.

Integrates with LiteLLM admin API to mirror workspace → LiteLLM Team and
user membership → LiteLLM API Key mappings for spend tracking.
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends
from api.auth_utils import get_current_user
from domain.entities.user import User

from api.schemas.workspaces import (
    AddMemberRequest,
    CreateWorkspaceRequest,
    MemberResponse,
    WorkspaceResponse,
)
from adapters.llm.litellm_admin import LiteLLMAdmin
from adapters.repositories.user_repository import SqlAlchemyUserRepository
from adapters.repositories.workspace_repository import SqlAlchemyWorkspaceRepository
from config import settings
from domain.entities.user_workspace import UserWorkspace
from domain.entities.workspace import Workspace
from infrastructure.database import async_session_factory

logger = logging.getLogger(__name__)

router = APIRouter(tags=["workspaces"])

_admin = LiteLLMAdmin(
    base_url=settings.LITELLM_BASE_URL,
    master_key=settings.LITELLM_MASTER_KEY,
)


# ── Workspace CRUD ────────────────────────────────────────────────────────


@router.post("/workspaces", response_model=WorkspaceResponse, status_code=201)
async def create_workspace(request: CreateWorkspaceRequest, current_user: User = Depends(get_current_user)) -> WorkspaceResponse:
    """Create a new workspace and mirror it as a LiteLLM Team."""
    workspace_id = str(uuid.uuid4())

    # 1. Create LiteLLM Team
    litellm_team_id: str | None = None
    try:
        team_data = await _admin.create_team(
            team_alias=request.name,
            models=request.allowed_models,
            max_budget=request.max_budget,
            budget_duration=request.budget_duration,
        )
        litellm_team_id = team_data.get("team_id")
    except Exception:
        logger.warning("LiteLLM team creation failed — continuing without it.")


    # 2. Persist locally
    async with async_session_factory() as session:
        repo = SqlAlchemyWorkspaceRepository(session)
        workspace = Workspace(
            id=workspace_id,
            name=request.name,
            created_at=datetime.now(timezone.utc).isoformat(),
            litellm_team_id=litellm_team_id,
        )
        created = await repo.create(workspace)
        
        # Make the creator an admin/owner of this workspace
        membership = UserWorkspace(
            user_id=current_user.id,
            workspace_id=workspace_id,
            role="admin",
            litellm_key=None,  # We can generate it if needed
        )
        await repo.add_member(membership)
        
        await session.commit()

        return WorkspaceResponse(
            id=created.id,
            name=created.name,
            created_at=created.created_at,
            litellm_team_id=created.litellm_team_id,
        )


@router.get("/workspaces", response_model=list[WorkspaceResponse])
async def list_workspaces(current_user: User = Depends(get_current_user)) -> list[WorkspaceResponse]:
    """List all workspaces."""
    async with async_session_factory() as session:
        repo = SqlAlchemyWorkspaceRepository(session)
        
        if current_user.is_admin:
            workspaces = await repo.list_all()
        else:
            memberships = await repo.get_user_workspaces(current_user.id)
            workspaces = []
            for m in memberships:
                ws = await repo.get_by_id(m.workspace_id)
                if ws:
                    workspaces.append(ws)

        return [
            WorkspaceResponse(
                id=w.id,
                name=w.name,
                created_at=w.created_at,
                litellm_team_id=w.litellm_team_id,
            )
            for w in workspaces
        ]


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(workspace_id: str, current_user: User = Depends(get_current_user)) -> WorkspaceResponse:
    """Get a workspace by ID."""
    async with async_session_factory() as session:
        repo = SqlAlchemyWorkspaceRepository(session)
        workspace = await repo.get_by_id(workspace_id)

        if not workspace:
            raise HTTPException(
                status_code=404, detail=f"Workspace '{workspace_id}' not found."
            )
            
        if not current_user.is_admin:
            memberships = await repo.get_user_workspaces(current_user.id)
            if not any(m.workspace_id == workspace_id for m in memberships):
                raise HTTPException(status_code=403, detail="Not a member of this workspace.")

        return WorkspaceResponse(
            id=workspace.id,
            name=workspace.name,
            created_at=workspace.created_at,
            litellm_team_id=workspace.litellm_team_id,
        )


# ── Membership ────────────────────────────────────────────────────────────


@router.post(
    "/workspaces/{workspace_id}/members",
    response_model=MemberResponse,
    status_code=201,
)
async def add_member(
    workspace_id: str, request: AddMemberRequest, current_user: User = Depends(get_current_user)
) -> MemberResponse:
    """Add a user to a workspace and generate a LiteLLM API key for them."""
    async with async_session_factory() as session:
        ws_repo = SqlAlchemyWorkspaceRepository(session)
        user_repo = SqlAlchemyUserRepository(session)

        workspace = await ws_repo.get_by_id(workspace_id)
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found.")

        user = await user_repo.get_by_id(request.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")

        # Generate LiteLLM key for user in this team
        litellm_key_alias: str | None = None
        if workspace.litellm_team_id:
            try:
                key_data = await _admin.generate_key(
                    user_id=user.id,
                    team_id=workspace.litellm_team_id,
                )
                litellm_key_alias = key_data.get("key")
            except Exception:
                logger.warning(
                    "LiteLLM key generation failed — continuing without it."
                )

        membership = UserWorkspace(
            user_id=request.user_id,
            workspace_id=workspace_id,
            role=request.role,
            litellm_key=litellm_key_alias,
        )
        await ws_repo.add_member(membership)
        await session.commit()

        return MemberResponse(
            user_id=user.id,
            user_name=user.name,
            user_email=user.email,
            role=request.role,
            litellm_key_alias=litellm_key_alias,
        )


@router.get(
    "/workspaces/{workspace_id}/members",
    response_model=list[MemberResponse],
)
async def list_members(workspace_id: str, current_user: User = Depends(get_current_user)) -> list[MemberResponse]:
    """List all members of a workspace."""
    async with async_session_factory() as session:
        ws_repo = SqlAlchemyWorkspaceRepository(session)
        user_repo = SqlAlchemyUserRepository(session)

        workspace = await ws_repo.get_by_id(workspace_id)
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found.")

        memberships = await ws_repo.get_members(workspace_id)
        results: list[MemberResponse] = []

        for m in memberships:
            user = await user_repo.get_by_id(m.user_id)
            if user:
                results.append(
                    MemberResponse(
                        user_id=user.id,
                        user_name=user.name,
                        user_email=user.email,
                        role=m.role,
                        litellm_key_alias=m.litellm_key,
                    )
                )

        return results
