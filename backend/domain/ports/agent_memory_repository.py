"""Agent memory repository port — abstract interface for agent memory storage."""

from abc import ABC, abstractmethod


class IAgentMemoryRepository(ABC):
    """Abstract interface for agent memory (key-value store scoped by workspace)."""

    @abstractmethod
    async def remember(self, workspace_id: str, key: str, value: str) -> None:
        """Store a fact in memory for a workspace."""
        pass

    @abstractmethod
    async def recall(self, workspace_id: str, key: str) -> str | None:
        """Retrieve a fact from memory for a workspace. Returns None if not found."""
        pass

    @abstractmethod
    async def list_all(self, workspace_id: str) -> dict[str, str]:
        """Return all memory entries for a workspace as a dict."""
        pass

    @abstractmethod
    async def clear(self, workspace_id: str) -> None:
        """Clear all memory entries for a workspace."""
        pass
