"""Schemas for the /conversations endpoints."""

from pydantic import BaseModel, Field


class ConversationResponse(BaseModel):
    """A single conversation entry."""

    id: str
    workspace_id: str
    created_by: str
    title: str
    created_at: str | None = None
    updated_at: str | None = None


class MessageResponse(BaseModel):
    """A single message within a conversation."""

    id: str
    conversation_id: str
    role: str
    content: str
    model: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    created_at: str | None = None
    tool_calls: list | dict | None = None


class ConversationDetailResponse(BaseModel):
    """A conversation with its messages."""

    conversation: ConversationResponse
    messages: list[MessageResponse] = []


class UpdateConversationRequest(BaseModel):
    """Request body for updating a conversation."""

    title: str = Field(..., min_length=1, max_length=500)
