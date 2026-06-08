"""Database infrastructure — async SQLAlchemy engine, session factory, and table creation."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from config import settings

from sqlalchemy.pool import NullPool

DATABASE_URL: str = settings.APP_DATABASE_URL

async_engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    poolclass=NullPool,
)

async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Declarative base for all SQLAlchemy ORM models."""


async def create_tables() -> None:
    """Create all tables defined by ORM models.

    Should be called once at application startup (e.g. in a FastAPI
    ``lifespan`` handler).  Importing ``infrastructure.models`` before
    calling this function ensures every model is registered on ``Base``.
    """
    # Ensure models are imported so Base.metadata is populated.
    import infrastructure.models as _models  # noqa: F401

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
