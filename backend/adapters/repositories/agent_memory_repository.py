"""SQLAlchemy agent memory repository — stores agent memory facts in the database."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from domain.ports.agent_memory_repository import IAgentMemoryRepository
from infrastructure.models import AgentMemoryModel


class SqlAlchemyAgentMemoryRepository(IAgentMemoryRepository):
    """Agent memory repository backed by SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def remember(self, workspace_id: str, key: str, value: str) -> None:
        """Store or update a fact in memory for a workspace."""
        result = await self._session.execute(
            select(AgentMemoryModel).where(
                AgentMemoryModel.workspace_id == workspace_id,
                AgentMemoryModel.memory_key == key,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.memory_value = value
        else:
            model = AgentMemoryModel(
                id=str(uuid.uuid4()),
                workspace_id=workspace_id,
                memory_key=key,
                memory_value=value,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            self._session.add(model)
        await self._session.flush()

    async def recall(self, workspace_id: str, key: str) -> str | None:
        """Retrieve a fact from memory for a workspace."""
        # Exact match first
        result = await self._session.execute(
            select(AgentMemoryModel).where(
                AgentMemoryModel.workspace_id == workspace_id,
                AgentMemoryModel.memory_key == key,
            )
        )
        model = result.scalar_one_or_none()
        if model:
            return model.memory_value if isinstance(model.memory_value, str) else json.dumps(model.memory_value)

        # Partial match fallback
        result = await self._session.execute(
            select(AgentMemoryModel).where(
                AgentMemoryModel.workspace_id == workspace_id,
            )
        )
        all_entries = result.scalars().all()
        key_lower = key.lower()
        for entry in all_entries:
            if key_lower in entry.memory_key.lower() or entry.memory_key.lower() in key_lower:
                val = entry.memory_value if isinstance(entry.memory_value, str) else json.dumps(entry.memory_value)
                return f"Recalled: '{entry.memory_key}' = '{val}'"

        return None

    async def list_all(self, workspace_id: str) -> dict[str, str]:
        """Return all memory entries for a workspace."""
        result = await self._session.execute(
            select(AgentMemoryModel).where(
                AgentMemoryModel.workspace_id == workspace_id,
            )
        )
        entries = result.scalars().all()
        return {
            entry.memory_key: (entry.memory_value if isinstance(entry.memory_value, str) else json.dumps(entry.memory_value))
            for entry in entries
        }

    async def clear(self, workspace_id: str) -> None:
        """Clear all memory entries for a workspace."""
        await self._session.execute(
            delete(AgentMemoryModel).where(
                AgentMemoryModel.workspace_id == workspace_id,
            )
        )
        await self._session.flush()
