import pytest
from httpx import AsyncClient
from sqlalchemy.future import select
from infrastructure.database import async_session_factory
from infrastructure.models import FeedbackModel
from domain.entities.user import User


@pytest.mark.asyncio
async def test_create_feedback_success(client: AsyncClient) -> None:
    """POST /api/feedback should successfully store feedback and return 201."""
    payload = {
        "user_id": "test-user-id",
        "workspace_id": None,
        "rating": 4,
        "category": "UI/UX",
        "comment": "Nice glassmorphic UI, very clean!"
    }
    
    response = await client.post("/api/feedback", json=payload)
    assert response.status_code == 201
    
    data = response.json()
    assert data["id"] is not None
    assert data["rating"] == 4
    assert data["category"] == "UI/UX"
    assert data["comment"] == "Nice glassmorphic UI, very clean!"
    assert data["created_at"] is not None

    # Verify directly in SQLite
    async with async_session_factory() as session:
        result = await session.execute(select(FeedbackModel).where(FeedbackModel.id == data["id"]))
        db_feedback = result.scalar_one_or_none()
        assert db_feedback is not None
        assert db_feedback.rating == 4
        assert db_feedback.comment == "Nice glassmorphic UI, very clean!"


@pytest.mark.asyncio
async def test_create_feedback_invalid_category(client: AsyncClient) -> None:
    """POST /api/feedback with invalid category should return 422 validation error."""
    payload = {
        "user_id": "test-user-id",
        "rating": 5,
        "category": "InvalidCategoryName",
        "comment": "Should fail validation"
    }
    
    response = await client.post("/api/feedback", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_feedback_admin(client: AsyncClient) -> None:
    """GET /api/feedback should return a list of feedbacks when logged in as admin."""
    # Seed a feedback first
    async with async_session_factory() as session:
        feedback = FeedbackModel(
            id="test-feedback-id-1",
            user_id="test-user-id",
            rating=5,
            category="Bug",
            comment="Found a bug in workflow status.",
            created_at="2026-06-08T10:00:00Z"
        )
        session.add(feedback)
        await session.commit()

    response = await client.get("/api/feedback")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) >= 1
    # Check that our seeded feedback exists in the list
    seeded_feedback = next((f for f in data if f["id"] == "test-feedback-id-1"), None)
    assert seeded_feedback is not None
    assert seeded_feedback["category"] == "Bug"


@pytest.mark.asyncio
async def test_list_feedback_non_admin_forbidden(client: AsyncClient) -> None:
    """GET /api/feedback should return 403 when user is not admin."""
    from main import app
    from api.auth_utils import get_current_user

    async def mock_get_non_admin_user() -> User:
        return User(
            id="test-user-id-non-admin",
            name="Normal User",
            email="normal@example.com",
            is_admin=False,
            created_at="2026-06-04T10:00:00Z"
        )

    # Temporarily override auth dependency to return non-admin
    app.dependency_overrides[get_current_user] = mock_get_non_admin_user
    try:
        response = await client.get("/api/feedback")
        assert response.status_code == 403
        assert response.json()["detail"] == "Only administrators are allowed to view feedback logs."
    finally:
        # Restore default override
        from tests.conftest import mock_get_current_user
        app.dependency_overrides[get_current_user] = mock_get_current_user
