"""SQLAlchemy user repository adapter — concrete implementation of IUserRepository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.user import User
from domain.ports.user_repository import IUserRepository
from infrastructure.models import UserModel


class SqlAlchemyUserRepository(IUserRepository):
    """Concrete user repository backed by an async SQLAlchemy session.

    Each public method receives or creates its own session scope, ensuring
    the repository is safe to use across concurrent requests.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _to_entity(model: UserModel) -> User:
        """Map an ORM model instance to a domain entity."""
        return User(
            id=model.id,
            name=model.name,
            email=model.email,
            hashed_password=model.hashed_password,
            is_admin=model.is_admin,
            created_at=model.created_at,
        )

    # ── IUserRepository implementation ──────────────────────────────

    async def create(self, user: User) -> User:
        """Persist a new user and return the stored entity."""
        model = UserModel(
            id=user.id,
            name=user.name,
            email=user.email,
            hashed_password=user.hashed_password,
            is_admin=user.is_admin,
            **({"created_at": user.created_at} if user.created_at else {}),
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def get_by_id(self, user_id: str) -> User | None:
        """Return a user by ID, or ``None`` if not found."""
        result = await self._session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_email(self, email: str) -> User | None:
        """Return a user by email address, or ``None`` if not found."""
        result = await self._session.execute(
            select(UserModel).where(UserModel.email == email)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_all(self) -> list[User]:
        """Return every user in the system."""
        result = await self._session.execute(select(UserModel))
        return [self._to_entity(m) for m in result.scalars().all()]
