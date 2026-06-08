"""Schemas for the /workspaces endpoints."""

from pydantic import BaseModel, Field


class CreateWorkspaceRequest(BaseModel):
    """Request body for creating a workspace."""

    name: str = Field(..., min_length=1, description="Workspace display name.")
    allowed_models: list[str] = Field(
        default_factory=list,
        description="List of model names this workspace can access (e.g. ['nova-lite', 'gemini-flash']).",
    )
    max_budget: float | None = Field(default=None, description="Optional maximum budget in USD.")
    budget_duration: str | None = Field(default=None, description="Optional budget duration (e.g. '30d', '24h').")



class AddMemberRequest(BaseModel):
    """Request body for adding a user to a workspace."""

    user_id: str = Field(..., description="ID of the user to add.")
    role: str = Field(default="member", description="Role: 'admin' or 'member'.")


class WorkspaceResponse(BaseModel):
    """Response body containing workspace details."""

    id: str
    name: str
    created_at: str | None = None
    litellm_team_id: str | None = None


class MemberResponse(BaseModel):
    """Response body for a workspace member."""

    user_id: str
    user_name: str
    user_email: str
    role: str
    litellm_key_alias: str | None = None
