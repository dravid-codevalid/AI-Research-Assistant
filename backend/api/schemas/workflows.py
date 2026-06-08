from __future__ import annotations
from pydantic import BaseModel, Field, field_validator


class WorkflowSubmitRequest(BaseModel):
    """Request body to submit a research task for async workflow processing."""

    question: str = Field(
        ..., min_length=1, description="The research question to be processed asynchronously."
    )

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        from api.security import sanitize_and_check_prompt
        try:
            return sanitize_and_check_prompt(v)
        except ValueError as exc:
            raise ValueError(str(exc))
    workspace_id: str = Field(..., description="Workspace context ID.")
    user_id: str | None = Field(
        default=None, description="Optional User ID for attribution context."
    )


class WorkflowSubmitResponse(BaseModel):
    """Response body after submitting a research task."""

    workflow_id: str = Field(..., description="Unique Temporal Workflow ID for tracking.")
    status: str = Field(..., description="Submission status (e.g., QUEUED).")


class ToolCallSchema(BaseModel):
    """A dictionary entry tracking a tool invocation during the task."""

    tool: str
    input: str
    output: str


class WorkflowStatusResponse(BaseModel):
    """Full detail of the workflow research task status and results."""

    workflow_id: str = Field(..., description="Temporal Workflow ID.")
    status: str = Field(..., description="Task status (QUEUED, PROCESSING, COMPLETED, FAILED).")
    question: str = Field(..., description="Original question submitted.")
    answer: str | None = Field(default=None, description="Final agent answer if task is complete.")
    tool_calls: list[ToolCallSchema] | None = Field(
        default=None, description="Ordered tool trace if execution ran tools."
    )
    created_at: str = Field(..., description="Task submission timestamp.")
    updated_at: str = Field(..., description="Task modification timestamp.")
