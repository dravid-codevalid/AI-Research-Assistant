"""Tests for the /ask endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ask_valid_question_returns_200(client: AsyncClient) -> None:
    """POST /api/ask with a valid question should return 200."""
    response = await client.post(
        "/api/ask",
        json={"question": "What is machine learning?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "model" in data
    assert data["model"] == "echo-v1"


@pytest.mark.asyncio
async def test_ask_empty_question_returns_422(client: AsyncClient) -> None:
    """POST /api/ask with an empty question should return 422."""
    response = await client.post(
        "/api/ask",
        json={"question": ""},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_ask_response_contains_echo(client: AsyncClient) -> None:
    """The echo adapter should include the original question in its response."""
    question = "Tell me about neural networks"
    response = await client.post(
        "/api/ask",
        json={"question": question},
    )
    assert response.status_code == 200
    data = response.json()
    assert "I received your question" in data["answer"]
    assert question in data["answer"]


@pytest.mark.asyncio
async def test_ask_missing_question_returns_422(client: AsyncClient) -> None:
    """POST /api/ask with no question field should return 422."""
    response = await client.post("/api/ask", json={})
    assert response.status_code == 422
