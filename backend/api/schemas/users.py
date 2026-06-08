"""Schemas for the /users endpoints."""

from pydantic import BaseModel, Field


class CreateUserRequest(BaseModel):
    """Request body for creating a user."""

    name: str = Field(..., min_length=1, description="Display name for the user.")
    email: str = Field(..., min_length=3, description="User email address.")


class UserResponse(BaseModel):
    """Response body containing user details."""

    id: str
    name: str
    email: str
    is_admin: bool = False
    created_at: str | None = None
