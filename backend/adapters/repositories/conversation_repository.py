"""SQLAlchemy conversation repository — concrete implementation of IConversationRepository."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.conversation import Conversation
from domain.entities.message import Message
import uuid
from domain.ports.conversation_repository import IConversationRepository
from infrastructure.models import ConversationModel, MessageModel, TokenUsageLogModel


class SqlAlchemyConversationRepository(IConversationRepository):
    """Concrete conversation repository backed by an async SQLAlchemy session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _to_conversation_entity(model: ConversationModel) -> Conversation:
        """Map a ConversationModel to a domain Conversation entity."""
        return Conversation(
            id=model.id,
            workspace_id=model.workspace_id,
            created_by=model.created_by,
            title=model.title,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _to_message_entity(model: MessageModel) -> Message:
        """Map a MessageModel to a domain Message entity."""
        return Message(
            id=model.id,
            conversation_id=model.conversation_id,
            role=model.role,
            content=model.content,
            model=model.model,
            prompt_tokens=model.prompt_tokens,
            completion_tokens=model.completion_tokens,
            total_tokens=model.total_tokens,
            created_at=model.created_at,
            tool_calls=model.tool_calls,
        )

    # ── Conversation CRUD ──────────────────────────────────────────────

    async def create_conversation(self, conversation: Conversation) -> Conversation:
        """Persist a new conversation and return the stored entity."""
        model = ConversationModel(
            id=conversation.id,
            workspace_id=conversation.workspace_id,
            created_by=conversation.created_by,
            title=conversation.title,
            **({"created_at": conversation.created_at} if conversation.created_at else {}),
            **({"updated_at": conversation.updated_at} if conversation.updated_at else {}),
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_conversation_entity(model)

    async def get_conversation_by_id(self, conversation_id: str) -> Conversation | None:
        """Return a conversation by ID, or None if not found."""
        result = await self._session.execute(
            select(ConversationModel).where(ConversationModel.id == conversation_id)
        )
        model = result.scalar_one_or_none()
        return self._to_conversation_entity(model) if model else None

    async def list_conversations_by_workspace(
        self, workspace_id: str
    ) -> list[Conversation]:
        """Return all conversations in a workspace, newest first."""
        result = await self._session.execute(
            select(ConversationModel)
            .where(ConversationModel.workspace_id == workspace_id)
            .order_by(desc(ConversationModel.updated_at))
        )
        return [self._to_conversation_entity(m) for m in result.scalars().all()]

    async def update_conversation_title(
        self, conversation_id: str, title: str
    ) -> Conversation | None:
        """Update the title and updated_at of a conversation."""
        result = await self._session.execute(
            select(ConversationModel).where(ConversationModel.id == conversation_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        model.title = title
        model.updated_at = datetime.now(timezone.utc).isoformat()
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_conversation_entity(model)

    async def update_conversation_timestamp(self, conversation_id: str) -> None:
        """Update only the updated_at timestamp of a conversation."""
        result = await self._session.execute(
            select(ConversationModel).where(ConversationModel.id == conversation_id)
        )
        model = result.scalar_one_or_none()
        if model:
            model.updated_at = datetime.now(timezone.utc).isoformat()
            await self._session.flush()

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and its messages. Return True if deleted."""
        result = await self._session.execute(
            select(ConversationModel).where(ConversationModel.id == conversation_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return False
        await self._session.delete(model)
        await self._session.flush()
        return True

    # ── Message CRUD ───────────────────────────────────────────────────

    async def add_message(self, message: Message) -> Message:
        """Persist a new message and return the stored entity."""
        model = MessageModel(
            id=message.id,
            conversation_id=message.conversation_id,
            role=message.role,
            content=message.content,
            model=message.model,
            prompt_tokens=message.prompt_tokens,
            completion_tokens=message.completion_tokens,
            total_tokens=message.total_tokens,
            tool_calls=message.tool_calls,
            **({"created_at": message.created_at} if message.created_at else {}),
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_message_entity(model)

    async def update_message_tokens(
        self,
        message_id: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
    ) -> None:
        """Update token counts on an existing message."""
        result = await self._session.execute(
            select(MessageModel).where(MessageModel.id == message_id)
        )
        model = result.scalar_one_or_none()
        if model:
            model.prompt_tokens = prompt_tokens
            model.completion_tokens = completion_tokens
            model.total_tokens = total_tokens
            await self._session.flush()

    async def get_messages(
        self, conversation_id: str, limit: int = 20
    ) -> list[Message]:
        """Return the most recent messages for a conversation, oldest first."""
        # Get the most recent `limit` messages, then reverse to oldest-first
        subq = (
            select(MessageModel)
            .where(MessageModel.conversation_id == conversation_id)
            .order_by(desc(MessageModel.created_at))
            .limit(limit)
            .subquery()
        )
        result = await self._session.execute(
            select(MessageModel)
            .join(subq, MessageModel.id == subq.c.id)
            .order_by(MessageModel.created_at)
        )
        return [self._to_message_entity(m) for m in result.scalars().all()]

    async def get_all_messages(self, conversation_id: str) -> list[Message]:
        """Return all messages for a conversation, oldest first."""
        result = await self._session.execute(
            select(MessageModel)
            .where(MessageModel.conversation_id == conversation_id)
            .order_by(MessageModel.created_at)
        )
        return [self._to_message_entity(m) for m in result.scalars().all()]

    # ── Token aggregation ──────────────────────────────────────────────

    async def get_token_usage(
        self,
        workspace_id: str | None = None,
        user_id: str | None = None,
    ) -> list[dict]:
        """Return aggregated token usage records grouped by model and user."""
        query = (
            select(
                MessageModel.model,
                ConversationModel.workspace_id,
                ConversationModel.created_by,
                func.sum(MessageModel.prompt_tokens).label("prompt_tokens"),
                func.sum(MessageModel.completion_tokens).label("completion_tokens"),
                func.sum(MessageModel.total_tokens).label("total_tokens"),
                func.count(MessageModel.id).label("request_count"),
                func.max(MessageModel.created_at).label("latest_at"),
            )
            .join(
                ConversationModel,
                MessageModel.conversation_id == ConversationModel.id,
            )
            .where(MessageModel.role == "assistant")
            .group_by(
                MessageModel.model,
                ConversationModel.workspace_id,
                ConversationModel.created_by,
            )
        )

        if workspace_id:
            query = query.where(ConversationModel.workspace_id == workspace_id)
        if user_id:
            query = query.where(ConversationModel.created_by == user_id)

        result = await self._session.execute(query)
        rows = result.all()
        return [
            {
                "model": row.model,
                "workspace_id": row.workspace_id,
                "user_id": row.created_by,
                "prompt_tokens": row.prompt_tokens or 0,
                "completion_tokens": row.completion_tokens or 0,
                "total_tokens": row.total_tokens or 0,
                "request_count": row.request_count or 0,
                "created_at": row.latest_at,
            }
            for row in rows
        ]

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
        model_instance = TokenUsageLogModel(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            user_id=user_id,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost=cost,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._session.add(model_instance)
        await self._session.flush()
