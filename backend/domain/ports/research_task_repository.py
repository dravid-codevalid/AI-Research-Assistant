from __future__ import annotations
from abc import ABC, abstractmethod
from domain.entities.research_task import ResearchTask


class IResearchTaskRepository(ABC):
    """Abstract interface for ResearchTask repository implementations."""

    @abstractmethod
    async def create(self, task: ResearchTask) -> ResearchTask:
        """Create a new research task record."""
        pass

    @abstractmethod
    async def get_by_id(self, task_id: str) -> ResearchTask | None:
        """Get a research task record by its ID."""
        pass

    @abstractmethod
    async def list_by_user(self, user_id: str, workspace_id: str | None = None) -> list[ResearchTask]:
        """List all research tasks created by a specific user, optionally filtered by workspace."""
        pass
