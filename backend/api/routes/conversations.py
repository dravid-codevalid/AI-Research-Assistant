"""Conversations route — CRUD endpoints for conversation management."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from api.auth_utils import get_current_user
from domain.entities.user import User

from adapters.repositories.conversation_repository import SqlAlchemyConversationRepository
from infrastructure.database import async_session_factory
from api.schemas.conversations import (
    ConversationResponse,
    ConversationDetailResponse,
    MessageResponse,
    UpdateConversationRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["conversations"])


async def _get_repo():
    """Provide a conversation repository with a fresh session."""
    async with async_session_factory() as session:
        repo = SqlAlchemyConversationRepository(session)
        yield repo, session


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
) -> list[ConversationResponse]:
    """List all conversations in a workspace."""
    async with async_session_factory() as session:
        repo = SqlAlchemyConversationRepository(session)
        conversations = await repo.list_conversations_by_workspace(workspace_id)
        return [
            ConversationResponse(
                id=c.id,
                workspace_id=c.workspace_id,
                created_by=c.created_by,
                title=c.title,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in conversations
        ]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
) -> ConversationDetailResponse:
    """Get a conversation with all its messages."""
    async with async_session_factory() as session:
        repo = SqlAlchemyConversationRepository(session)
        conversation = await repo.get_conversation_by_id(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        messages = await repo.get_all_messages(conversation_id)
        return ConversationDetailResponse(
            conversation=ConversationResponse(
                id=conversation.id,
                workspace_id=conversation.workspace_id,
                created_by=conversation.created_by,
                title=conversation.title,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at,
            ),
            messages=[
                MessageResponse(
                    id=m.id,
                    conversation_id=m.conversation_id,
                    role=m.role,
                    content=m.content,
                    model=m.model,
                    prompt_tokens=m.prompt_tokens,
                    completion_tokens=m.completion_tokens,
                    total_tokens=m.total_tokens,
                    created_at=m.created_at,
                    tool_calls=m.tool_calls,
                )
                for m in messages
            ],
        )


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    request: UpdateConversationRequest,
    current_user: User = Depends(get_current_user),
) -> ConversationResponse:
    """Rename a conversation."""
    async with async_session_factory() as session:
        repo = SqlAlchemyConversationRepository(session)
        conversation = await repo.get_conversation_by_id(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        updated = await repo.update_conversation_title(conversation_id, request.title)
        await session.commit()

        if not updated:
            raise HTTPException(status_code=500, detail="Failed to update conversation")

        return ConversationResponse(
            id=updated.id,
            workspace_id=updated.workspace_id,
            created_by=updated.created_by,
            title=updated.title,
            created_at=updated.created_at,
            updated_at=updated.updated_at,
        )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Delete a conversation (creator only)."""
    async with async_session_factory() as session:
        repo = SqlAlchemyConversationRepository(session)
        conversation = await repo.get_conversation_by_id(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Only the creator can delete
        if conversation.created_by != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Only the conversation creator can delete it",
            )

        deleted = await repo.delete_conversation(conversation_id)
        await session.commit()

        if not deleted:
            raise HTTPException(status_code=500, detail="Failed to delete conversation")

        return {"detail": "Conversation deleted"}
