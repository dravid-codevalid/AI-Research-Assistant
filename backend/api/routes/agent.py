"""Agent routes — POST /agent/ask, GET /agent/memory, DELETE /agent/memory."""

import asyncio
import json
import logging
import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from api.auth_utils import get_current_user
from api.schemas.agent import (
    AgentAskRequest,
    AgentAskResponse,
    MemoryResponse,
    ToolCallResponse,
    ModelInfoResponse,
)
from adapters.agent.streaming_agent import StreamingLiteLLMAgent
from adapters.repositories.workspace_repository import SqlAlchemyWorkspaceRepository
from adapters.repositories.agent_memory_repository import SqlAlchemyAgentMemoryRepository
from infrastructure.database import async_session_factory
from config import settings
from domain.entities.user import User
from use_cases.run_agent import RunAgentUseCase

logger = logging.getLogger(__name__)

router = APIRouter(tags=["agent"])

# MLflow model registry caching
_OPTIMIZED_MODEL = None
_MODEL_INFO = {
    "version": "default",
    "model_name": "gemini-flash",
    "val_score": None,
    "source": "fallback"
}


def load_optimized_model() -> None:
    """Load the latest optimized model version from the MLflow registry."""
    global _OPTIMIZED_MODEL, _MODEL_INFO
    try:
        import mlflow
        import mlflow.dspy
        from mlflow.tracking import MlflowClient

        mlflow.set_tracking_uri("http://localhost:5000")
        client = MlflowClient()

        versions = client.search_model_versions("name='research-assistant-agent'")
        if versions:
            latest = max(versions, key=lambda v: int(v.version))
            model_uri = f"models:/research-assistant-agent/{latest.version}"
            logger.info("Attempting to load optimized model from URI: %s", model_uri)

            _OPTIMIZED_MODEL = mlflow.dspy.load_model(model_uri)

            # Fetch run metrics/params for metadata
            try:
                run = client.get_run(latest.run_id)
                val_score = run.data.metrics.get("val_score", None)
                model_name = run.data.params.get("model_name", "Unknown")
            except Exception as run_exc:
                logger.warning("Failed to fetch run details for version %s: %s", latest.version, run_exc)
                val_score = None
                model_name = "Unknown"

            _MODEL_INFO = {
                "version": str(latest.version),
                "model_name": model_name,
                "val_score": val_score,
                "source": "mlflow"
            }
            logger.info(
                "Successfully loaded optimized model from MLflow: version=%s, model=%s, val_score=%s",
                latest.version, model_name, val_score
            )
        else:
            logger.info("No registered model version found for 'research-assistant-agent' in MLflow.")
    except Exception as exc:
        logger.warning(
            "Could not load optimized model from MLflow registry: %s. "
            "Falling back to default SimpleAgent.", exc
        )



async def _get_workspace_llm_key(user_id: str | None, workspace_id: str | None) -> str | None:
    if user_id and workspace_id:
        try:
            async with async_session_factory() as lookup_session:
                ws_repo = SqlAlchemyWorkspaceRepository(lookup_session)
                membership = await ws_repo.get_membership(user_id, workspace_id)
                if membership and membership.litellm_key:
                    return membership.litellm_key
        except Exception:
            logger.warning(
                "Failed to look up LiteLLM key for user '%s' in agent use case.",
                user_id,
            )
    return None

async def _get_agent_use_case(
    user_id: str | None = None,
    workspace_id: str | None = None,
) -> RunAgentUseCase:
    """Provide the RunAgentUseCase wired to the DSPy agent adapter with user key lookup."""
    litellm_api_key = await _get_workspace_llm_key(user_id, workspace_id)

    if _OPTIMIZED_MODEL is not None:
        from adapters.agent.dspy_agent import DSPyAgentAdapter
        agent = DSPyAgentAdapter(
            model_name="gemini-flash",
            litellm_base_url=settings.LITELLM_BASE_URL,
            api_key=litellm_api_key or settings.LITELLM_MASTER_KEY,
        )
    else:
        agent = StreamingLiteLLMAgent(
            model_name="gemini-flash",
            base_url=settings.LITELLM_BASE_URL,
            api_key=litellm_api_key or settings.LITELLM_MASTER_KEY,
        )
    return RunAgentUseCase(agent_provider=agent)


# ── Agent ask ─────────────────────────────────────────────────────────────


@router.post("/agent/ask", response_model=AgentAskResponse)
async def agent_ask(
    request: AgentAskRequest,
    current_user: User = Depends(get_current_user),
) -> AgentAskResponse:
    """Run the DSPy ReAct agent on a question.

    The agent uses web search and file-based memory tools
    to reason about and answer research questions.
    """
    use_case = await _get_agent_use_case(
        user_id=request.user_id or current_user.id,
        workspace_id=request.workspace_id,
    )

    try:
        result = await use_case.execute(
            question=request.question,
            user_id=request.user_id or current_user.id,
            workspace_id=request.workspace_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.error("Agent execution failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=502,
            detail=f"Agent error: {str(exc)}",
        )

    return AgentAskResponse(
        answer=result.answer,
        tool_calls=[
            ToolCallResponse(
                tool=tc.tool,
                input=tc.input,
                output=tc.output,
            )
            for tc in result.tool_calls
        ],
        model_used=result.model_used,
        thoughts=result.thoughts,
    )


# ── Memory viewer ─────────────────────────────────────────────────────────


@router.get("/agent/memory", response_model=MemoryResponse)
async def get_agent_memory(
    workspace_id: str | None = None,
    current_user: User = Depends(get_current_user),
) -> MemoryResponse:
    """Return the current contents of the agent's database memory."""
    wid = workspace_id or "default"
    async with async_session_factory() as session:
        repo = SqlAlchemyAgentMemoryRepository(session)
        memory = await repo.list_all(wid)
    return MemoryResponse(memory=memory)


@router.delete("/agent/memory", response_model=MemoryResponse)
async def clear_agent_memory(
    workspace_id: str | None = None,
    current_user: User = Depends(get_current_user),
) -> MemoryResponse:
    """Clear all facts from the agent's database memory."""
    wid = workspace_id or "default"
    async with async_session_factory() as session:
        repo = SqlAlchemyAgentMemoryRepository(session)
        await repo.clear(wid)
        await session.commit()
    return MemoryResponse(memory={})


# ── Streaming agent ask (SSE) ─────────────────────────────────────────────


@router.post("/agent/ask/stream")
async def agent_ask_stream(
    request: AgentAskRequest,
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Run the custom streaming agent and yield true streaming events."""
    user_id = request.user_id or current_user.id
    workspace_id = request.workspace_id

    litellm_api_key = await _get_workspace_llm_key(user_id, workspace_id)

    agent = StreamingLiteLLMAgent(
        model_name="gemini-flash",
        base_url=settings.LITELLM_BASE_URL,
        api_key=litellm_api_key or settings.LITELLM_MASTER_KEY,
    )

    async def sse_generator():
        try:
            async for event in agent.run_stream(
                question=request.question,
                user_id=user_id,
                workspace_id=workspace_id,
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'event': 'error', 'text': str(exc)})}\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")


@router.get("/agent/model-info", response_model=ModelInfoResponse)
async def get_model_info(
    current_user: User = Depends(get_current_user),
) -> ModelInfoResponse:
    """Return the active DSPy agent model details from MLflow registry."""
    return ModelInfoResponse(
        version=_MODEL_INFO.get("version", "default"),
        model_name=_MODEL_INFO.get("model_name", "gemini-flash"),
        val_score=_MODEL_INFO.get("val_score", None),
        source=_MODEL_INFO.get("source", "fallback")
    )


