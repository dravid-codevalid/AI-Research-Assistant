from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class ResearchTask:
    """Domain entity representing an asynchronous agent research task orchestrating via Temporal."""

    id: str
    workspace_id: str
    user_id: str
    question: str
    status: str = "QUEUED"
    answer: str | None = None
    tool_calls: list | dict | None = None
    created_at: str | None = None
    updated_at: str | None = None
