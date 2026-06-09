"""Message entity — core domain object representing a single chat message."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Message:
    """Immutable domain entity representing a chat message.

    Attributes:
        id: Unique identifier for the message (UUID string).
        conversation_id: The conversation this message belongs to.
        role: Message role — 'user', 'assistant', or 'system'.
        content: The text content of the message.
        model: Model used to generate the response (assistant messages only).
        prompt_tokens: Number of prompt tokens used for this exchange.
        completion_tokens: Number of completion tokens generated.
        total_tokens: Sum of prompt + completion tokens.
        created_at: ISO-8601 timestamp of message creation, or None if unset.
    """

    id: str
    conversation_id: str
    role: str
    content: str
    model: str | None = field(default=None)
    prompt_tokens: int = field(default=0)
    completion_tokens: int = field(default=0)
    total_tokens: int = field(default=0)
    created_at: str | None = field(default=None)
    tool_calls: list | dict | None = field(default=None)
