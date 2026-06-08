"""Echo LLM adapter — placeholder that echoes questions back."""

from domain.ports.llm_provider import ILLMProvider
from domain.value_objects.answer import Answer


class EchoLLM(ILLMProvider):
    """Placeholder LLM provider that echoes the question back.

    Used for Level 1 development and testing. Will be replaced
    by real AI integrations (AWS Bedrock, LiteLLM) in Level 2.
    """

    async def ask(
        self,
        question: str,
        system_prompt: str | None = None,
        messages: list[dict[str, str]] | None = None,
        user_id: str | None = None,
        workspace_id: str | None = None,
    ) -> Answer:
        """Return a placeholder echo response."""
        return Answer(
            text=(
                f"I received your question: {question}. "
                "This is a placeholder response — real AI integration "
                "is coming in Level 2!"
            ),
            model="echo-v1",
        )

    async def ask_stream(
        self,
        question: str,
        system_prompt: str | None = None,
        messages: list[dict[str, str]] | None = None,
        user_id: str | None = None,
        workspace_id: str | None = None,
    ):
        """Yield a placeholder echo response incrementally."""
        import asyncio
        response = f"I received your question: {question}. This is a streamed placeholder response!"
        words = response.split(" ")
        for i, word in enumerate(words):
            yield {"text": word + (" " if i < len(words) - 1 else ""), "model": "echo-v1"}
            await asyncio.sleep(0.05)
