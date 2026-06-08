from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.future import select
import uuid
from datetime import datetime, timezone

from api.schemas.feedback import FeedbackCreate, FeedbackResponse
from infrastructure.database import async_session_factory
from infrastructure.models import FeedbackModel
from api.auth_utils import get_current_user
from domain.entities.user import User

router = APIRouter(tags=["feedback"])


@router.post("/feedback", response_model=FeedbackResponse, status_code=201)
async def create_feedback(request: FeedbackCreate) -> FeedbackResponse:
    """Create a user feedback entry."""
    async with async_session_factory() as session:
        feedback_id = str(uuid.uuid4())
        created_at_str = datetime.now(timezone.utc).isoformat()

        # Build ORM model
        db_feedback = FeedbackModel(
            id=feedback_id,
            user_id=request.user_id,
            workspace_id=request.workspace_id,
            rating=request.rating,
            category=request.category,
            comment=request.comment,
            created_at=created_at_str,
        )

        session.add(db_feedback)
        await session.commit()

        return FeedbackResponse(
            id=db_feedback.id,
            user_id=db_feedback.user_id,
            workspace_id=db_feedback.workspace_id,
            rating=db_feedback.rating,
            category=db_feedback.category,
            comment=db_feedback.comment,
            created_at=db_feedback.created_at,
        )


@router.get("/feedback", response_model=list[FeedbackResponse])
async def list_feedback(current_user: User = Depends(get_current_user)) -> list[FeedbackResponse]:
    """List all user feedback entries (Admin only)."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only administrators are allowed to view feedback logs."
        )

    async with async_session_factory() as session:
        result = await session.execute(select(FeedbackModel).order_by(FeedbackModel.created_at.desc()))
        feedbacks = result.scalars().all()

        return [
            FeedbackResponse(
                id=f.id,
                user_id=f.user_id,
                workspace_id=f.workspace_id,
                rating=f.rating,
                category=f.category,
                comment=f.comment,
                created_at=f.created_at,
            )
            for f in feedbacks
        ]
