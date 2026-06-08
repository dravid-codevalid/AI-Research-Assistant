"""Run agent use case — orchestrates executing the DSPy ReAct agent."""

from __future__ import annotations

import logging

from domain.ports.agent_port import IAgentProvider
from domain.value_objects.agent_result import AgentResult

logger = logging.getLogger(__name__)


class RunAgentUseCase:
    """Use case for running the AI agent on a user's question.

    Delegates to the injected IAgentProvider adapter and returns
    the agent's result including the answer, tool call trace,
    and model information.
    """

    def __init__(self, agent_provider: IAgentProvider) -> None:
        self.agent_provider = agent_provider

    async def execute(
        self,
        question: str,
        user_id: str | None = None,
        workspace_id: str | None = None,
    ) -> AgentResult:
        """Execute the agent on the given question.

        Args:
            question: The user's research question.
            user_id: Optional user ID for attribution.
            workspace_id: Optional workspace ID for attribution.

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

        result = await self.agent_provider.run(
            question=question.strip(),
            user_id=user_id,
            workspace_id=workspace_id,
        )

        logger.info(
            "Agent completed: %d tool calls, model=%s",
            len(result.tool_calls),
            result.model_used,
        )

        return result
