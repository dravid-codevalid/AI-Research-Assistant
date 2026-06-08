"""User repository port — abstract interface for user persistence."""

from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.user import User


class IUserRepository(ABC):
    """Abstract interface for user data access.

    Concrete implementations (e.g. SQLAlchemy adapter) must satisfy
    this contract so the domain layer stays decoupled from infrastructure.
    """

    @abstractmethod
    async def create(self, user: User) -> User:
        """Persist a new user and return the stored entity."""

    @abstractmethod
    async def get_by_id(self, user_id: str) -> User | None:
        """Return a user by ID, or ``None`` if not found."""

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        """Return a user by email address, or ``None`` if not found."""

    @abstractmethod
    async def list_all(self) -> list[User]:
        """Return every user in the system."""
