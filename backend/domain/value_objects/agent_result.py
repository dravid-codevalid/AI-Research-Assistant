"""Agent result value objects — represents the output of an AI agent run."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ToolCallRecord:
    """Immutable record of a single tool invocation by the agent.

    Attributes:
        tool: Name of the tool that was called.
        input: The input/arguments passed to the tool.
        output: The result returned by the tool.
    """

    tool: str
    input: str
    output: str


@dataclass(frozen=True)
class AgentResult:
    """Immutable value object representing the output of an agent run.

    Attributes:
        answer: The agent's final answer text.
        tool_calls: Ordered list of tool invocations made during reasoning.
        model_used: Identifier of the LLM model used by the agent.
    """

    answer: str
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    model_used: str = ""
    thoughts: list[str] = field(default_factory=list)

