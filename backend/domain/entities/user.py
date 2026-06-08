"""User entity — core domain object representing an application user."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class User:
    """Immutable domain entity representing a registered user.

    Attributes:
        id: Unique identifier for the user (UUID string).
        name: Display name of the user.
        email: Email address (used for authentication lookups).
        created_at: ISO-8601 timestamp of account creation, or None if unset.
    """

    id: str
    name: str
    email: str
    hashed_password: str | None = field(default=None)
    is_admin: bool = field(default=False)
    created_at: str | None = field(default=None)
