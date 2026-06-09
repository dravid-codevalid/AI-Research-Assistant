"""Conversation repository port — abstract interface for conversation persistence."""

from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.conversation import Conversation
from domain.entities.message import Message


class IConversationRepository(ABC):
    """Abstract interface for conversation and message data access.

    Concrete implementations (e.g. SQLAlchemy adapter) must satisfy
    this contract so the domain layer stays decoupled from infrastructure.
    """

    # ── Conversation CRUD ──────────────────────────────────────────────

    @abstractmethod
    async def create_conversation(self, conversation: Conversation) -> Conversation:
        """Persist a new conversation and return the stored entity."""

    @abstractmethod
    async def get_conversation_by_id(self, conversation_id: str) -> Conversation | None:
        """Return a conversation by ID, or ``None`` if not found."""

    @abstractmethod
    async def list_conversations_by_workspace(
        self, workspace_id: str
    ) -> list[Conversation]:
        """Return all conversations in a workspace, newest first."""

    @abstractmethod
    async def update_conversation_title(
        self, conversation_id: str, title: str
    ) -> Conversation | None:
        """Update the title of a conversation. Return updated entity or None."""

    @abstractmethod
    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and its messages. Return True if deleted."""

    # ── Message CRUD ───────────────────────────────────────────────────

    @abstractmethod
    async def add_message(self, message: Message) -> Message:
        """Persist a new message and return the stored entity."""

    @abstractmethod
    async def get_messages(
        self, conversation_id: str, limit: int = 20
    ) -> list[Message]:
        """Return the most recent messages for a conversation, oldest first."""

    @abstractmethod
    async def get_all_messages(self, conversation_id: str) -> list[Message]:
        """Return all messages for a conversation, oldest first."""

    # ── Token aggregation ──────────────────────────────────────────────

    @abstractmethod
    async def get_token_usage(
        self,
        workspace_id: str | None = None,
        user_id: str | None = None,
    ) -> list[dict]:
        """Return aggregated token usage records, optionally filtered."""

    @abstractmethod
    async def log_token_usage(
        self,
        workspace_id: str,
        user_id: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        cost: float | None = None,
    ) -> None:
        """Log a token usage record to the database for tracking."""
