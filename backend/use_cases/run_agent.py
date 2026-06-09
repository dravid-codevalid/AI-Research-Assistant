"""Run agent use case — orchestrates executing the DSPy ReAct agent."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from domain.ports.agent_port import IAgentProvider
from domain.ports.conversation_repository import IConversationRepository
from domain.entities.conversation import Conversation
from domain.entities.message import Message
from domain.value_objects.agent_result import AgentResult

logger = logging.getLogger(__name__)


class RunAgentUseCase:
    """Use case for running the AI agent on a user's question.

    Delegates to the injected IAgentProvider adapter and returns
    the agent's result including the answer, tool call trace,
    and model information. Optionally persists the agent chat 
    in the database if a conversation repository is supplied.
    """

    def __init__(
        self,
        agent_provider: IAgentProvider,
        conversation_repo: IConversationRepository | None = None,
    ) -> None:
        self.agent_provider = agent_provider
        self.conversation_repo = conversation_repo

    async def _get_or_create_conversation(
        self,
        conversation_id: str | None,
        user_id: str | None,
        workspace_id: str | None,
        question: str,
    ) -> str:
        """Return (conversation_id). Creates a new conversation if needed."""
        if not self.conversation_repo:
            return conversation_id or str(uuid.uuid4())

        if conversation_id:
            existing = await self.conversation_repo.get_conversation_by_id(
                conversation_id
            )
            if existing:
                return conversation_id

        # Create a new conversation
        new_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        # Title of conversation
        title = question.strip()
        if len(title) > 50:
            title = title[:47] + "..."

        conversation = Conversation(
            id=new_id,
            workspace_id=workspace_id,
            created_by=user_id,
            title=title,
            created_at=now,
            updated_at=now,
        )
        await self.conversation_repo.create_conversation(conversation)
        return new_id

    async def _save_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        model: str | None = None,
        tool_calls: list | dict | None = None,
    ) -> None:
        """Persist a message to the database."""
        if not self.conversation_repo:
            return

        message = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role=role,
            content=content,
            model=model,
            created_at=datetime.now(timezone.utc).isoformat(),
            tool_calls=tool_calls,
        )
        await self.conversation_repo.add_message(message)
        await self.conversation_repo.update_conversation_timestamp(conversation_id)

    async def execute(
        self,
        question: str,
        user_id: str | None = None,
        workspace_id: str | None = None,
        conversation_id: str | None = None,
    ) -> AgentResult:
        """Execute the agent on the given question.

        Args:
            question: The user's research question.
            user_id: Optional user ID for attribution.
            workspace_id: Optional workspace ID for attribution.
            conversation_id: Optional conversation ID to persist under.

        Returns:
            An AgentResult with the answer and tool call trace.

        Raises:
            ValueError: If the question is empty or whitespace-only.
        """
        if not question or not question.strip():
            raise ValueError("Question must not be empty.")

        logger.info(
            "Running agent for question: '%s' (user=%s, workspace=%s)",
            question[:80],
            user_id,
            workspace_id,
        )

        from adapters.agent.dspy_agent import _active_db_session
        session_token = None
        if hasattr(self, '_session') and self._session:
            session_token = _active_db_session.set(self._session)

        try:
            # 1. Get or create conversation and save user message immediately
            conv_id = await self._get_or_create_conversation(
                conversation_id, user_id, workspace_id, question
            )
            await self._save_message(conv_id, "user", question.strip())

            # Commit the user message immediately so it's not lost
            if hasattr(self, '_session') and self._session:
                await self._session.commit()

            # 2. Run the agent
            result = await self.agent_provider.run(
                question=question.strip(),
                user_id=user_id,
                workspace_id=workspace_id,
            )

            # 3. Save assistant response with tool calls
            serialized_tool_calls = [
                {"tool": tc.tool, "input": tc.input, "output": tc.output}
                for tc in result.tool_calls
            ]
            
            # Format thoughts and final answer into message content
            content = result.answer
            
            await self._save_message(
                conv_id,
                "assistant",
                content,
                model=result.model_used,
                tool_calls=serialized_tool_calls,
            )

            # 4. Log token usage to DB (Agent runs consume tokens!)
            if workspace_id and user_id:
                try:
                    if result.prompt_tokens is not None and result.completion_tokens is not None:
                        prompt_tokens = result.prompt_tokens
                        completion_tokens = result.completion_tokens
                    else:
                        # Fallback estimation
                        prompt_tokens = len(question) // 4 + 100
                        completion_tokens = len(result.answer) // 4 + 100
                        for tc in result.tool_calls:
                            prompt_tokens += len(tc.input) // 4
                            completion_tokens += len(tc.output) // 4

                    await self.conversation_repo.log_token_usage(
                        workspace_id=workspace_id,
                        user_id=user_id,
                        model=result.model_used or "unknown",
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=prompt_tokens + completion_tokens,
                        cost=None,
                    )
                except Exception as log_exc:
                    logger.warning("Failed to log token usage for agent: %s", log_exc)

            # Commit the session with assistant message and usage log
            if hasattr(self, '_session') and self._session:
                await self._session.commit()

            # Create a new AgentResult with the conversation ID (since AgentResult is frozen)
            final_result = AgentResult(
                answer=result.answer,
                tool_calls=result.tool_calls,
                model_used=result.model_used,
                thoughts=result.thoughts,
                conversation_id=conv_id,
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
                total_tokens=result.total_tokens,
            )

        finally:
            if session_token:
                _active_db_session.reset(session_token)
            if hasattr(self, '_session') and self._session:
                await self._session.close()

        logger.info(
            "Agent completed: %d tool calls, model=%s",
            len(final_result.tool_calls),
            final_result.model_used,
        )

        return final_result
