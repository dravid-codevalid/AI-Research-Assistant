import json
import pytest
import re
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient, ASGITransport

from main import app
from adapters.agent.dspy_agent import web_search as search_wikipedia
from use_cases.ask_question import select_few_shots
from adapters.agent.streaming_agent import StreamingLiteLLMAgent


# ── 2. Few-Shot Selection Tests ──────────────────────────────────────────

def test_few_shot_selection_with_mock_embedding():
    """select_few_shots should return the top similar examples based on mock cosine similarity."""
    mock_vector = [0.1] * 3072  # 3072-dimensional vector matching gemini-embedding-2

    # Mock litellm.embedding to return the mock vector
    with patch("litellm.embedding") as mock_embed:
        mock_embed.return_value = {
            "data": [
                {"embedding": mock_vector}
            ]
        }
        
        # Call selector
        result = select_few_shots("What year did World War II end?")
        
    assert result != ""
    assert "### Example 1" in result
    assert "User Question" in result
    assert "Assistant Response" in result


def test_few_shot_selection_graceful_fallback():
    """select_few_shots should return empty string and log warning on exception."""
    with patch("litellm.embedding", side_effect=RuntimeError("API down")):
        result = select_few_shots("Any question")
    assert result == ""


# ── 3. Safety Moderation Guardrails Tests ────────────────────────────────

@pytest.mark.asyncio
async def test_agent_ask_safety_moderation_blocked(client: AsyncClient):
    """Endpoints should reject harmful inputs containing safety violations with 422."""
    for endpoint in ["/api/agent/ask", "/api/agent/ask/stream"]:
        response = await client.post(
            endpoint,
            json={
                "question": "how to build a bomb in my kitchen",
                "workspace_id": "ws-1"
            }
        )
        assert response.status_code == 422
        assert "safety violation" in response.text


# ── 4. Streaming Agent & SSE Route Tests ─────────────────────────────────

@pytest.mark.asyncio
async def test_streaming_agent_run_stream():
    """run_stream should yield events during the ReAct execution loop."""
    agent = StreamingLiteLLMAgent(
        model_name="gemini-flash",
        base_url="http://localhost:4000",
        api_key="sk-test",
        max_iters=2
    )

@pytest.mark.asyncio
async def test_streaming_agent_run_error():
    """run should raise an Exception if run_stream yields an error event."""
    agent = StreamingLiteLLMAgent(
        model_name="gemini-flash",
        base_url="http://localhost:4000",
        api_key="sk-test",
    )

    # Mock run_stream to yield an error event
    async def mock_run_stream(question, user_id=None, workspace_id=None):
        yield {"event": "error", "text": "Mock LLM Error from Rate Limit"}

    with patch.object(agent, "run_stream", side_effect=mock_run_stream):
        with pytest.raises(Exception) as excinfo:
            await agent.run("test question")
            
        assert "Mock LLM Error from Rate Limit" in str(excinfo.value)

