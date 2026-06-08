from __future__ import annotations
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.research_task import ResearchTask
from domain.ports.research_task_repository import IResearchTaskRepository
from infrastructure.models import ResearchTaskModel


class SqlAlchemyResearchTaskRepository(IResearchTaskRepository):
    """SqlAlchemy concrete implementation of the IResearchTaskRepository port."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_entity(model: ResearchTaskModel) -> ResearchTask:
        return ResearchTask(
            id=model.id,
            workspace_id=model.workspace_id,
            user_id=model.user_id,
            question=model.question,
            status=model.status,
            answer=model.answer,
            tool_calls=model.tool_calls,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def create(self, task: ResearchTask) -> ResearchTask:
        now = datetime.now(timezone.utc).isoformat()
        model = ResearchTaskModel(
            id=task.id,
            workspace_id=task.workspace_id,
            user_id=task.user_id,
            question=task.question,
            status=task.status,
            answer=task.answer,
            tool_calls=task.tool_calls,
            created_at=task.created_at or now,
            updated_at=task.updated_at or now,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def get_by_id(self, task_id: str) -> ResearchTask | None:
        result = await self._session.execute(
            select(ResearchTaskModel).where(ResearchTaskModel.id == task_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_by_user(self, user_id: str, workspace_id: str | None = None) -> list[ResearchTask]:
        query = select(ResearchTaskModel).where(ResearchTaskModel.user_id == user_id)
        if workspace_id:
            query = query.where(ResearchTaskModel.workspace_id == workspace_id)
        query = query.order_by(ResearchTaskModel.created_at.desc())
        
        result = await self._session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]
