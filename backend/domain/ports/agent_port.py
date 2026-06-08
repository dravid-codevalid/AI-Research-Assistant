"""Agent provider port — abstract interface for AI agent implementations."""

from abc import ABC, abstractmethod

from domain.value_objects.agent_result import AgentResult


class IAgentProvider(ABC):
    """Abstract interface for AI agent adapters.

    An agent accepts a question and autonomously decides which tools
    to use (if any) before producing a final answer.
    """

    @abstractmethod
    async def run(
        self,
        question: str,
        user_id: str | None = None,
        workspace_id: str | None = None,
    ) -> AgentResult:
        """Run the agent on the given question.

        Args:
            question: The user's research question.
            user_id: Optional user ID for attribution.
            workspace_id: Optional workspace ID for attribution.

        Returns:
            An AgentResult containing the answer, tool call trace, and model info.
        """
        pass
