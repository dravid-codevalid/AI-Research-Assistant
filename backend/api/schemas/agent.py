"""Schemas for the /agent endpoints."""

from pydantic import BaseModel, Field, field_validator


class AgentAskRequest(BaseModel):
    """Request body for asking the AI agent a question."""

    question: str = Field(
        ..., min_length=1, description="The question for the AI agent."
    )

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        from api.security import sanitize_and_check_prompt
        try:
            return sanitize_and_check_prompt(v)
        except ValueError as exc:
            raise ValueError(str(exc))

    user_id: str | None = Field(
        default=None,
        description="User ID for attribution (Level 3+).",
    )
    workspace_id: str | None = Field(
        default=None,
        description="Workspace ID for attribution (Level 3+).",
    )
    conversation_id: str | None = Field(
        default=None,
        description="Conversation ID to persist under or resume.",
    )


class ToolCallResponse(BaseModel):
    """A single tool invocation made by the agent."""

    tool: str = Field(..., description="Name of the tool called.")
    input: str = Field(..., description="Input/arguments passed to the tool.")
    output: str = Field(..., description="Result returned by the tool.")


class AgentAskResponse(BaseModel):
    """Response from the AI agent containing the answer and tool trace."""

    answer: str = Field(..., description="The agent's final answer.")
    tool_calls: list[ToolCallResponse] = Field(
        default_factory=list,
        description="Ordered list of tool invocations made during reasoning.",
    )
    model_used: str | None = Field(
        default=None,
        description="Identifier of the LLM model used by the agent.",
    )
    thoughts: list[str] = Field(
        default_factory=list,
        description="Ordered list of agent reasoning steps.",
    )
    conversation_id: str | None = Field(
        default=None,
        description="ID of the conversation in the database.",
    )



class MemoryResponse(BaseModel):
    """Current contents of the agent's file-based memory."""

    memory: dict[str, str] = Field(
        default_factory=dict,
        description="Key-value pairs stored in the agent's memory.",
    )


class ModelInfoResponse(BaseModel):
    """Details about the active model version loaded from MLflow."""

    version: str = Field(..., description="The registered model version from MLflow, or 'default'.")
    model_name: str = Field(..., description="The LLM model type (e.g. 'gemini-flash').")
    val_score: float | None = Field(default=None, description="Validation score logged for this model version.")
    source: str = Field(..., description="Whether the model is loaded from 'mlflow' or running on 'fallback'.")

