"""Schemas for the /ask endpoint."""

from pydantic import BaseModel, Field, field_validator

from adapters.llm.model_registry import DEFAULT_MODEL_ID


class AskRequest(BaseModel):
    """Request body for asking a question."""

    question: str = Field(..., min_length=1, description="The question to ask the AI.")

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        from api.security import sanitize_and_check_prompt
        try:
            return sanitize_and_check_prompt(v)
        except ValueError as exc:
            raise ValueError(str(exc))

    messages: list[dict[str, str]] = Field(
        default_factory=list,
        description="Optional list of previous messages (frontend fallback).",
    )
    conversation_id: str | None = Field(
        default=None,
        description="Existing conversation ID. If None, a new conversation is created.",
    )
    model_id: str = Field(
        default=DEFAULT_MODEL_ID,
        description="Bedrock model ID or LiteLLM model name to use.",
    )
    user_id: str | None = Field(
        default=None,
        description="User ID for spend tracking (Level 3+).",
    )
    workspace_id: str | None = Field(
        default=None,
        description="Workspace ID for spend tracking (Level 3+).",
    )


class AskResponse(BaseModel):
    """Response body containing the AI answer."""

    answer: str
    model: str
    conversation_id: str | None = None


class ModelInfoResponse(BaseModel):
    """A single model entry returned by GET /models."""

    id: str
    display_name: str
    provider: str
    description: str
    context_window: int
