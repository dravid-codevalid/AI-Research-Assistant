"""Answer value object — represents a response from an LLM provider."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Answer:
    """Immutable value object representing an LLM answer.

    Attributes:
        text: The generated response text.
        model: Model identifier or display label.
        prompt_tokens: Number of prompt tokens used (0 if unavailable).
        completion_tokens: Number of completion tokens generated (0 if unavailable).
        total_tokens: Sum of prompt + completion tokens (0 if unavailable).
        created_at: Timestamp of when the answer was generated.
    """

    text: str
    model: str
    prompt_tokens: int = field(default=0)
    completion_tokens: int = field(default=0)
    total_tokens: int = field(default=0)
    created_at: datetime = field(default_factory=datetime.now)
