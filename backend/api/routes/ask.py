"""Ask route — POST /ask, POST /ask/stream, and GET /models endpoints."""

import json

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from api.auth_utils import get_current_user
from domain.entities.user import User

from api.dependencies import get_ask_use_case_for_model
from api.schemas.ask import AskRequest, AskResponse, ModelInfoResponse
from adapters.llm.model_registry import list_models

router = APIRouter(tags=["ask"])


# ── Model listing ─────────────────────────────────────────────────────────

@router.get("/models", response_model=list[ModelInfoResponse])
async def get_available_models() -> list[ModelInfoResponse]:
    """Return the catalog of available LLM models."""
    return [
        ModelInfoResponse(
            id=m.id,
            display_name=m.display_name,
            provider=m.provider,
            description=m.description,
            context_window=m.context_window,
        )
        for m in list_models()
    ]


# ── Synchronous ask ───────────────────────────────────────────────────────

@router.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest, current_user: User = Depends(get_current_user)) -> AskResponse:
    """Ask a question and receive an AI-generated answer."""
    request.user_id = current_user.id
    try:
        use_case = await get_ask_use_case_for_model(
            model_id=request.model_id,
            user_id=request.user_id,
            workspace_id=request.workspace_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        answer, conversation_id = await use_case.execute(
            request.question,
            user_id=request.user_id,
            workspace_id=request.workspace_id,
            conversation_id=request.conversation_id,
        )
    except Exception as exc:
        detail = str(exc)
        # Extract HTTP status from httpx errors if available
        status = 502
        if hasattr(exc, 'response') and hasattr(exc.response, 'status_code'):
            status = exc.response.status_code
        raise HTTPException(status_code=status, detail=f"LLM provider error: {detail}")

    return AskResponse(answer=answer.text, model=answer.model, conversation_id=conversation_id)


# ── Streaming ask (SSE) ──────────────────────────────────────────────────

@router.post("/ask/stream")
async def ask_question_stream(request: AskRequest, current_user: User = Depends(get_current_user)) -> StreamingResponse:
    """Ask a question and receive a streamed AI-generated answer in SSE format."""
    request.user_id = current_user.id
    try:
        use_case = await get_ask_use_case_for_model(
            model_id=request.model_id,
            user_id=request.user_id,
            workspace_id=request.workspace_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    async def sse_generator():
        try:
            async for chunk in use_case.execute_stream(
                request.question,
                user_id=request.user_id,
                workspace_id=request.workspace_id,
                conversation_id=request.conversation_id,
            ):
                yield f"data: {json.dumps(chunk)}\n\n"
        except Exception as exc:
            error_payload = {"error": True, "text": f"Streaming error: {exc}"}
            yield f"data: {json.dumps(error_payload)}\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")
