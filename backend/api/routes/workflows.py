from __future__ import annotations
import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException
from temporalio.client import Client

from api.auth_utils import get_current_user
from domain.entities.user import User
from config import settings
from infrastructure.database import async_session_factory
from adapters.repositories.research_task_repository import SqlAlchemyResearchTaskRepository
from domain.entities.research_task import ResearchTask
from api.schemas.workflows import (
    WorkflowSubmitRequest,
    WorkflowSubmitResponse,
    WorkflowStatusResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["workflows"])


async def _get_temporal_client() -> Client:
    """Connect to local Temporal server and return client."""
    return await Client.connect(settings.TEMPORAL_HOST)


@router.post("/workflows/submit", response_model=WorkflowSubmitResponse, status_code=201)
async def submit_workflow(
    request: WorkflowSubmitRequest,
    current_user: User = Depends(get_current_user),
) -> WorkflowSubmitResponse:
    """Submit a research question for async agent execution via Temporal."""
    user_id = request.user_id or current_user.id
    task_uuid = str(uuid.uuid4())
    workflow_id = f"research-{user_id}-{task_uuid}"

    # 1. Start Temporal Workflow (Non-blocking)
    try:
        from worker import ResearchWorkflow
        temporal_client = await _get_temporal_client()
        await temporal_client.start_workflow(
            ResearchWorkflow.run,
            args=[request.question, user_id, request.workspace_id],
            id=workflow_id,
            task_queue=settings.TEMPORAL_TASK_QUEUE,
        )
        logger.info(f"Started Temporal workflow '{workflow_id}' for user '{user_id}'")
    except Exception as exc:
        logger.error(f"Failed to start Temporal workflow: {exc}", exc_info=True)
        raise HTTPException(
            status_code=502,
            detail=f"Temporal workflow orchestrator unavailable: {exc}",
        )

    # 2. Persist metadata in local DB
    async with async_session_factory() as session:
        repo = SqlAlchemyResearchTaskRepository(session)
        task = ResearchTask(
            id=workflow_id,
            workspace_id=request.workspace_id,
            user_id=user_id,
            question=request.question,
            status="QUEUED",
        )
        await repo.create(task)
        await session.commit()

    return WorkflowSubmitResponse(workflow_id=workflow_id, status="QUEUED")


@router.get("/workflows/{workflow_id}/status", response_model=WorkflowStatusResponse)
async def get_workflow_status(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
) -> WorkflowStatusResponse:
    """Retrieve details and status of a research task workflow by ID."""
    async with async_session_factory() as session:
        repo = SqlAlchemyResearchTaskRepository(session)
        task = await repo.get_by_id(workflow_id)

    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Research task with workflow ID '{workflow_id}' not found.",
        )

    # Security check: User must be admin or the task creator
    if not current_user.is_admin and task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this task.")

    return WorkflowStatusResponse(
        workflow_id=task.id,
        status=task.status,
        question=task.question,
        answer=task.answer,
        tool_calls=task.tool_calls,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@router.get("/workflows", response_model=list[WorkflowStatusResponse])
async def list_workflows(
    user_id: str | None = None,
    workspace_id: str | None = None,
    current_user: User = Depends(get_current_user),
) -> list[WorkflowStatusResponse]:
    """List research workflows submitted by a user."""
    target_user_id = user_id or current_user.id

    # Security check: User must be admin or listing their own tasks
    if not current_user.is_admin and target_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to list tasks for other users.")

    async with async_session_factory() as session:
        repo = SqlAlchemyResearchTaskRepository(session)
        tasks = await repo.list_by_user(target_user_id, workspace_id)

    return [
        WorkflowStatusResponse(
            workflow_id=t.id,
            status=t.status,
            question=t.question,
            answer=t.answer,
            tool_calls=t.tool_calls,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in tasks
    ]

import asyncio
import json
from sse_starlette.sse import EventSourceResponse

@router.post("/workflows/{workflow_id}/cancel")
async def cancel_workflow(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
):
    """Cancel an in-flight research workflow."""
    async with async_session_factory() as session:
        repo = SqlAlchemyResearchTaskRepository(session)
        task = await repo.get_by_id(workflow_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if not current_user.is_admin and task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        temporal_client = await _get_temporal_client()
        handle = temporal_client.get_workflow_handle(workflow_id)
        await handle.cancel()
        
        async with async_session_factory() as session:
            repo = SqlAlchemyResearchTaskRepository(session)
            await repo.update(workflow_id, status="FAILED", answer="Workflow cancelled by user.")
            await session.commit()
            
    except Exception as exc:
        logger.error(f"Failed to cancel Temporal workflow: {exc}")
        raise HTTPException(status_code=500, detail="Failed to cancel workflow")
        
    return {"detail": "Workflow cancelled"}


@router.get("/workflows/{workflow_id}/stream")
async def stream_workflow_status(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
):
    """Stream workflow status updates via Server-Sent Events (SSE)."""
    async with async_session_factory() as session:
        repo = SqlAlchemyResearchTaskRepository(session)
        task = await repo.get_by_id(workflow_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if not current_user.is_admin and task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    async def event_generator():
        last_status = None
        while True:
            async with async_session_factory() as session:
                repo = SqlAlchemyResearchTaskRepository(session)
                task = await repo.get_by_id(workflow_id)
            
            if not task:
                break
                
            if task.status != last_status:
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "status": task.status,
                        "answer": task.answer,
                        "tool_calls": task.tool_calls
                    })
                }
                last_status = task.status
                
            if task.status in ["COMPLETED", "FAILED"]:
                break
                
            await asyncio.sleep(1)

    return EventSourceResponse(event_generator())
