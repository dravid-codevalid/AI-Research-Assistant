import asyncio
from datetime import datetime, timezone, timedelta
import logging
from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Worker
from sqlalchemy import update

from config import settings
from infrastructure.database import async_session_factory
from infrastructure.models import ResearchTaskModel
from adapters.agent.streaming_agent import StreamingLiteLLMAgent
from use_cases.run_agent import RunAgentUseCase
from adapters.repositories.workspace_repository import SqlAlchemyWorkspaceRepository

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("temporal-worker")


@activity.defn
async def run_agent_activity(question: str, user_id: str | None, workspace_id: str | None) -> dict:
    """Temporal activity that runs the DSPy Research Agent and updates local task status."""
    workflow_id = activity.info().workflow_id
    logger.info(f"Starting agent activity for task ID: {workflow_id}")

    # 1. Update status to PROCESSING
    async with async_session_factory() as session:
        await session.execute(
            update(ResearchTaskModel)
            .where(ResearchTaskModel.id == workflow_id)
            .values(
                status="PROCESSING", 
                updated_at=datetime.now(timezone.utc).isoformat()
            )
        )
        await session.commit()

    # 2. Look up LiteLLM key for workspace/user
    litellm_api_key = None
    if user_id and workspace_id:
        try:
            async with async_session_factory() as lookup_session:
                ws_repo = SqlAlchemyWorkspaceRepository(lookup_session)
                membership = await ws_repo.get_membership(user_id, workspace_id)
                if membership and membership.litellm_key:
                    litellm_api_key = membership.litellm_key
        except Exception as exc:
            logger.warning(f"Failed to lookup LiteLLM key for task {workflow_id}: {exc}")

    # 3. Initialize Agent Use Case
    try:
        if settings.LLM_PROVIDER.lower() == "echo":
            from unittest.mock import MagicMock
            result = MagicMock()
            result.answer = f"Echo response for: {question}"
            result.tool_calls = []
            result.model_used = "echo"
            result.thoughts = "Mock thoughts"
        else:
            agent = StreamingLiteLLMAgent(
                model_name="gemini-flash",
                base_url=settings.LITELLM_BASE_URL,
                api_key=litellm_api_key or settings.LITELLM_MASTER_KEY,
                source_page="queue",
            )
            
            db_session = async_session_factory()
            from adapters.repositories.conversation_repository import SqlAlchemyConversationRepository
            conversation_repo = SqlAlchemyConversationRepository(db_session)
            
            use_case = RunAgentUseCase(
                agent_provider=agent,
                conversation_repo=conversation_repo,
            )
            use_case._session = db_session
            
            result = await use_case.execute(
                question=question,
                user_id=user_id,
                workspace_id=workspace_id,
            )

        serialized_tool_calls = [
            {"tool": tc.tool, "input": tc.input, "output": tc.output}
            for tc in result.tool_calls
        ]

        # Update database with final answer and complete status
        async with async_session_factory() as session:
            await session.execute(
                update(ResearchTaskModel)
                .where(ResearchTaskModel.id == workflow_id)
                .values(
                    status="COMPLETED",
                    answer=result.answer,
                    tool_calls=serialized_tool_calls,
                    updated_at=datetime.now(timezone.utc).isoformat()
                )
            )
            await session.commit()

        return {
            "answer": result.answer,
            "tool_calls": serialized_tool_calls,
            "model_used": result.model_used,
            "thoughts": result.thoughts
        }

    except Exception as exc:
        logger.error(f"Agent activity failed for task {workflow_id}: {exc}", exc_info=True)
        async with async_session_factory() as session:
            await session.execute(
                update(ResearchTaskModel)
                .where(ResearchTaskModel.id == workflow_id)
                .values(
                    status="FAILED",
                    answer=f"Error running agent: {exc}",
                    updated_at=datetime.now(timezone.utc).isoformat()
                )
            )
            await session.commit()
        raise exc


@workflow.defn(sandboxed=False)
class ResearchWorkflow:
    """Temporal workflow that orchestrates the research agent activity with retries."""

    @workflow.run
    async def run(self, question: str, user_id: str | None, workspace_id: str | None) -> dict:
        from temporalio.common import RetryPolicy

        return await workflow.execute_activity(
            run_agent_activity,
            args=[question, user_id, workspace_id],
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=RetryPolicy(
                maximum_attempts=3,  # 1 initial + 2 retries
            )
        )


async def main():
    # Connect to local Temporal server
    client = await Client.connect(settings.TEMPORAL_HOST)
    logger.info(f"Connected to Temporal server at {settings.TEMPORAL_HOST}")

    # Start Worker
    worker = Worker(
        client,
        task_queue=settings.TEMPORAL_TASK_QUEUE,
        workflows=[ResearchWorkflow],
        activities=[run_agent_activity],
    )
    logger.info(f"Worker running on queue '{settings.TEMPORAL_TASK_QUEUE}'...")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
