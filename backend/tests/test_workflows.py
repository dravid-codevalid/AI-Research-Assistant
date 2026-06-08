import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.mark.asyncio
async def test_submit_workflow_returns_201():
    """Endpoint POST /api/workflows/submit should return 201 and start Temporal workflow."""
    mock_client = AsyncMock()
    with patch("api.routes.workflows._get_temporal_client", return_value=mock_client):
        with patch(
            "adapters.repositories.research_task_repository.SqlAlchemyResearchTaskRepository.create",
            new_callable=AsyncMock,
        ) as mock_create:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                response = await ac.post(
                    "/api/workflows/submit",
                    json={
                        "question": "What is clean architecture?",
                        "workspace_id": "ws-test-id",
                    },
                )
            assert response.status_code == 201
            data = response.json()
            assert "workflow_id" in data
            assert data["status"] == "QUEUED"
            assert mock_create.called


@pytest.mark.asyncio
async def test_get_workflow_status_not_found():
    """Endpoint GET /api/workflows/{id}/status should return 404 if task not found."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/workflows/non-existent-id/status")
    assert response.status_code == 404
