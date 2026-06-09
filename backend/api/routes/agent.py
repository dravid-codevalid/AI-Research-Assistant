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
from adapters.repositories.conversation_repository import SqlAlchemyConversationRepository
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
    if not settings.USE_MLFLOW_REGISTRY:
        logger.info("MLflow Model Registry integration is disabled via configuration.")
        return
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

    if settings.USE_MLFLOW_REGISTRY and _OPTIMIZED_MODEL is not None:
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

    session = async_session_factory()
    conversation_repo = SqlAlchemyConversationRepository(session)

    use_case = RunAgentUseCase(
        agent_provider=agent,
        conversation_repo=conversation_repo,
    )
    use_case._session = session
    return use_case


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
            conversation_id=request.conversation_id,
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
        conversation_id=result.conversation_id,
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
    conversation_id = request.conversation_id

    session = async_session_factory()
    conversation_repo = SqlAlchemyConversationRepository(session)

    try:
        if conversation_id:
            existing = await conversation_repo.get_conversation_by_id(conversation_id)
            if not existing:
                conversation_id = None

        if not conversation_id:
            import uuid
            from datetime import datetime, timezone
            from domain.entities.conversation import Conversation
            conversation_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat()
            
            title = request.question.strip()
            if len(title) > 50:
                title = title[:47] + "..."
                
            conversation = Conversation(
                id=conversation_id,
                workspace_id=workspace_id,
                created_by=user_id,
                title=title,
                created_at=now,
                updated_at=now,
            )
            await conversation_repo.create_conversation(conversation)

        # Save user message immediately
        import uuid
        from datetime import datetime, timezone
        from domain.entities.message import Message
        user_msg = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role="user",
            content=request.question.strip(),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        await conversation_repo.add_message(user_msg)
        await conversation_repo.update_conversation_timestamp(conversation_id)
        await session.commit()
    except Exception as exc:
        await session.close()
        logger.error("Failed to initialize conversation for agent stream: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize conversation: {str(exc)}",
        )

    litellm_api_key = await _get_workspace_llm_key(user_id, workspace_id)

    agent = StreamingLiteLLMAgent(
        model_name="gemini-flash",
        base_url=settings.LITELLM_BASE_URL,
        api_key=litellm_api_key or settings.LITELLM_MASTER_KEY,
    )

    async def sse_generator():
        try:
            # Yield conversation ID first
            yield f"data: {json.dumps({'event': 'conversation_id', 'conversation_id': conversation_id})}\n\n"

            thoughts = []
            tool_calls_record = []
            final_answer = ""
            model_used = "gemini-flash"

            async for event in agent.run_stream(
                question=request.question,
                user_id=user_id,
                workspace_id=workspace_id,
            ):
                if event.get("event") == "thought" and event.get("text"):
                    thoughts.append(event["text"])
                elif event.get("event") == "tool_call":
                    tool_calls_record.append({
                        "tool": event.get("tool"),
                        "input": event.get("input"),
                        "output": event.get("output"),
                    })
                elif event.get("event") == "token" and event.get("text"):
                    final_answer += event["text"]
                    if event.get("model_used"):
                        model_used = event["model_used"]
                elif event.get("event") == "done":
                    if event.get("answer"):
                        final_answer = event["answer"]
                    if event.get("thoughts"):
                        thoughts = event["thoughts"]
                    if event.get("tool_calls"):
                        tool_calls_record = event["tool_calls"]
                    if event.get("model_used"):
                        model_used = event["model_used"]

                yield f"data: {json.dumps(event)}\n\n"

            # Save assistant response
            import uuid
            from datetime import datetime, timezone
            from domain.entities.message import Message
            assistant_msg = Message(
                id=str(uuid.uuid4()),
                conversation_id=conversation_id,
                role="assistant",
                content=final_answer.strip(),
                model=model_used,
                created_at=datetime.now(timezone.utc).isoformat(),
                tool_calls=tool_calls_record,
            )
            await conversation_repo.add_message(assistant_msg)
            await conversation_repo.update_conversation_timestamp(conversation_id)

            # Log token usage to DB
            if workspace_id and user_id:
                try:
                    # Estimate token usage
                    prompt_est = len(request.question) // 4 + 100
                    completion_est = len(final_answer) // 4 + 100
                    for tc in tool_calls_record:
                        prompt_est += len(str(tc.get("input", ""))) // 4
                        completion_est += len(str(tc.get("output", ""))) // 4

                    await conversation_repo.log_token_usage(
                        workspace_id=workspace_id,
                        user_id=user_id,
                        model=model_used or "unknown",
                        prompt_tokens=prompt_est,
                        completion_tokens=completion_est,
                        total_tokens=prompt_est + completion_est,
                        cost=None,
                    )
                except Exception as log_exc:
                    logger.warning("Failed to log token usage for agent stream: %s", log_exc)

            await session.commit()
        except Exception as exc:
            logger.error("Error in agent_ask_stream generator: %s", exc, exc_info=True)
            yield f"data: {json.dumps({'event': 'error', 'text': str(exc)})}\n\n"
        finally:
            await session.close()

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


