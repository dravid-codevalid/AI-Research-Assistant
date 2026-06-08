"""AWS Bedrock LLM adapter.

Implements ILLMProvider for any model accessible via the AWS Bedrock
Converse / ConverseStream APIs.  The adapter is model-agnostic — the
caller specifies the model_id at construction time rather than reading
a single hard-coded value from config.
"""

import asyncio
import logging

import boto3
from botocore.exceptions import ClientError

from config import settings
from domain.ports.llm_provider import ILLMProvider
from domain.value_objects.answer import Answer
from adapters.llm.model_registry import get_model

logger = logging.getLogger(__name__)


class BedrockLLM(ILLMProvider):
    """LLM provider that calls AWS Bedrock using boto3.

    Parameters
    ----------
    model_id : str
        The Bedrock model identifier (e.g. ``us.amazon.nova-lite-v1:0``).
    """

    def __init__(self, model_id: str) -> None:
        self.client = boto3.client(
            "bedrock-runtime", region_name=settings.AWS_REGION
        )
        self.model_id = model_id
        self._model_info = get_model(model_id)

    # ── helpers ────────────────────────────────────────────────────────────

    @property
    def display_name(self) -> str:
        return self._model_info.display_name

    def _call_bedrock_converse(
        self, question: str, system_prompt: str | None
    ) -> str:
        """Synchronously call the Bedrock Converse API."""
        messages = [{"role": "user", "content": [{"text": question}]}]
        system = [{"text": system_prompt}] if system_prompt else []

        try:
            response = self.client.converse(
                modelId=self.model_id,
                messages=messages,
                system=system,
            )
            return response["output"]["message"]["content"][0]["text"]
        except ClientError as exc:
            error_code = exc.response["Error"]["Code"]
            error_msg = exc.response["Error"]["Message"]
            if error_code == "ThrottlingException":
                raise RuntimeError(
                    f"Bedrock rate limit exceeded for model '{self.model_id}'. "
                    f"Please retry in a moment."
                ) from exc
            elif error_code == "AccessDeniedException":
                raise RuntimeError(
                    f"Access denied for Bedrock model '{self.model_id}'. "
                    f"Check your AWS credentials and model access permissions."
                ) from exc
            elif error_code == "ValidationException":
                raise RuntimeError(
                    f"Invalid request to Bedrock model '{self.model_id}': {error_msg}"
                ) from exc
            else:
                raise RuntimeError(
                    f"Bedrock error ({error_code}): {error_msg}"
                ) from exc

    # ── ILLMProvider interface ─────────────────────────────────────────────

    async def ask(
        self,
        question: str,
        system_prompt: str | None = None,
        messages: list[dict[str, str]] | None = None,
        user_id: str | None = None,
        workspace_id: str | None = None,
        source_page: str | None = None,
    ) -> Answer:
        """Send a question to AWS Bedrock and return the answer."""
        answer_text = await asyncio.to_thread(
            self._call_bedrock_converse, question, system_prompt
        )
        return Answer(
            text=answer_text,
            model=f"Answered by {self.display_name}",
        )

    async def ask_stream(
        self,
        question: str,
        system_prompt: str | None = None,
        messages: list[dict[str, str]] | None = None,
        user_id: str | None = None,
        workspace_id: str | None = None,
        source_page: str | None = None,
    ):
        """Send a question to AWS Bedrock and yield the answer incrementally."""
        messages = [{"role": "user", "content": [{"text": question}]}]
        system = [{"text": system_prompt}] if system_prompt else []
        display = self.display_name

        queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def _boto_stream_worker() -> None:
            try:
                response = self.client.converse_stream(
                    modelId=self.model_id,
                    messages=messages,
                    system=system,
                )
                for chunk in response["stream"]:
                    if "contentBlockDelta" in chunk:
                        text = chunk["contentBlockDelta"]["delta"].get("text")
                        if text:
                            loop.call_soon_threadsafe(
                                queue.put_nowait,
                                {"text": text, "model": f"Answered by {display}"},
                            )
            except ClientError as exc:
                error_code = exc.response["Error"]["Code"]
                error_msg = exc.response["Error"]["Message"]
                err = RuntimeError(f"Bedrock streaming error ({error_code}): {error_msg}")
                loop.call_soon_threadsafe(queue.put_nowait, err)
            except Exception as exc:
                loop.call_soon_threadsafe(queue.put_nowait, exc)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)  # EOF

        asyncio.create_task(asyncio.to_thread(_boto_stream_worker))

        while True:
            item = await queue.get()
            if item is None:
                break
            if isinstance(item, Exception):
                raise item
            yield item
