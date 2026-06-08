"""LLM provider port — abstract interface for language model integrations."""

from abc import ABC, abstractmethod

from domain.value_objects.answer import Answer


class ILLMProvider(ABC):
    """Abstract interface for LLM provider adapters."""

    @abstractmethod
    async def ask(
        self,
        question: str,
        system_prompt: str | None = None,
        messages: list[dict[str, str]] | None = None,
        user_id: str | None = None,
        workspace_id: str | None = None,
        source_page: str | None = None,
    ) -> Answer:
        """Send a question to the LLM and return an Answer."""
        pass

    @abstractmethod
    async def ask_stream(
        self,
        question: str,
        system_prompt: str | None = None,
        messages: list[dict[str, str]] | None = None,
        user_id: str | None = None,
        workspace_id: str | None = None,
        source_page: str | None = None,
    ):
        """Send a question to the LLM and yield streaming chunks (AsyncGenerator[dict, None])."""
        pass
