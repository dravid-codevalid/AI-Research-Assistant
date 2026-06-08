"""Schemas for the /usage endpoint."""

from pydantic import BaseModel


class UsageRecord(BaseModel):
    """A single usage/spend record."""

    request_id: str | None = None
    user_id: str | None = None
    user_name: str | None = None
    team_id: str | None = None
    workspace_name: str | None = None
    model: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    spend: float = 0.0
    created_at: str | None = None
    source: str | None = None  # "database" or "litellm"
    source_page: str | None = None  # "chat", "agent", "queue"


class PageBreakdown(BaseModel):
    """Token/spend breakdown for a single page/feature."""
    page: str  # "chat", "agent", "queue"
    total_tokens: int = 0
    total_spend: float = 0.0
    request_count: int = 0


class UsageResponse(BaseModel):
    """Response body for usage data."""

    records: list[UsageRecord] = []
    total_spend: float = 0.0
    total_tokens: int = 0
    page_breakdown: list[PageBreakdown] = []
