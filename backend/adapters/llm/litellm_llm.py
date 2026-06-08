"""LiteLLM proxy LLM adapter.

Implements :class:`ILLMProvider` by calling the LiteLLM proxy's
OpenAI-compatible ``/v1/chat/completions`` endpoint.  Supports both
one-shot and streaming responses, and forwards user/workspace metadata
for spend attribution.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from domain.ports.llm_provider import ILLMProvider
from domain.value_objects.answer import Answer

logger = logging.getLogger(__name__)

# Default request timeout in seconds.
_DEFAULT_TIMEOUT = 60.0


class LiteLLMLLM(ILLMProvider):
    """LLM provider that routes requests through a LiteLLM proxy.

    Parameters
    ----------
    base_url : str
        Root URL of the LiteLLM proxy (e.g. ``http://localhost:4000``).
    api_key : str
        Per-user LiteLLM API key (generated via ``/key/generate``).
    model_name : str
        Friendly model alias from ``litellm_config.yaml``
        (e.g. ``nova-lite``, ``gemini-flash``, ``groq-llama``).
    """

    def __init__(self, base_url: str, api_key: str, model_name: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model_name = model_name

    # ── helpers ────────────────────────────────────────────────────────────

    def _headers(
        self,
        user_id: str | None = None,
        workspace_id: str | None = None,
    ) -> dict[str, str]:
        """Build request headers with auth and optional metadata."""
        headers: dict[str, str] = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if user_id:
            headers["x-litellm-user-id"] = user_id
        if workspace_id:
            headers["x-litellm-team-id"] = workspace_id
        return headers

    def _build_messages(
        self,
        question: str,
        system_prompt: str | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> list[dict[str, str]]:
        """Construct the ``messages`` array for chat completions."""
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": question})
        return messages

    @property
    def _completions_url(self) -> str:
        return f"{self.base_url}/v1/chat/completions"

    # ── ILLMProvider — one-shot ────────────────────────────────────────────

    async def ask(
        self,
        question: str,
        system_prompt: str | None = None,
        messages: list[dict[str, str]] | None = None,
        user_id: str | None = None,
        workspace_id: str | None = None,
        source_page: str | None = None,
    ) -> Answer:
        """Send a question to the LiteLLM proxy and return an Answer."""
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": self._build_messages(question, system_prompt, messages),
            "stream": False,
        }
        if source_page is not None:
            payload["metadata"] = {"source_page": source_page}

        try:
            async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
                response = await client.post(
                    self._completions_url,
                    headers=self._headers(user_id, workspace_id),
                    json=payload,
                )
                response.raise_for_status()
                data: dict[str, Any] = response.json()

            # Parse the OpenAI-compatible response
            text = data["choices"][0]["message"]["content"]
            model_id = data.get("model", self.model_name)

            # Extract token usage if available
            usage = data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0) or 0
            completion_tokens = usage.get("completion_tokens", 0) or 0
            total_tokens = usage.get("total_tokens", 0) or 0

            return Answer(
                text=text,
                model=f"Answered by {model_id}",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            )

        except httpx.HTTPStatusError as exc:
            logger.error(
                "LiteLLM ask failed [%s]: %s — %s",
                self.model_name,
                exc.response.status_code,
                exc.response.text,
            )
            raise
        except httpx.RequestError as exc:
            logger.error(
                "Network error during LiteLLM ask [%s]: %s",
                self.model_name,
                exc,
            )
            raise
        except (KeyError, IndexError) as exc:
            logger.error(
                "Unexpected response structure from LiteLLM [%s]: %s",
                self.model_name,
                exc,
            )
            raise

    # ── ILLMProvider — streaming ───────────────────────────────────────────

    async def ask_stream(
        self,
        question: str,
        system_prompt: str | None = None,
        messages: list[dict[str, str]] | None = None,
        user_id: str | None = None,
        workspace_id: str | None = None,
        source_page: str | None = None,
    ) -> AsyncGenerator[dict[str, str], None]:
        """Stream the LLM response, yielding ``{text, model}`` dicts.

        Connects to the proxy with ``stream=True`` and
        ``stream_options.include_usage=True`` to capture token counts
        in the final chunk. The last yielded dict includes ``usage`` data.
        """
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": self._build_messages(question, system_prompt, messages),
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if source_page is not None:
            payload["metadata"] = {"source_page": source_page}

        try:
            async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
                async with client.stream(
                    "POST",
                    self._completions_url,
                    headers=self._headers(user_id, workspace_id),
                    json=payload,
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        # SSE lines are prefixed with "data: "
                        if not line.startswith("data: "):
                            continue

                        data_str = line[len("data: "):]

                        # The stream terminates with "data: [DONE]"
                        if data_str.strip() == "[DONE]":
                            break

                        try:
                            chunk: dict[str, Any] = json.loads(data_str)
                        except json.JSONDecodeError:
                            logger.warning(
                                "Skipping malformed SSE chunk: %s", data_str
                            )
                            continue

                        # Check for usage data in the chunk (sent at the end)
                        usage = chunk.get("usage")
                        if usage:
                            yield {
                                "text": "",
                                "model": chunk.get("model", self.model_name),
                                "usage": json.dumps({
                                    "prompt_tokens": usage.get("prompt_tokens", 0),
                                    "completion_tokens": usage.get("completion_tokens", 0),
                                    "total_tokens": usage.get("total_tokens", 0),
                                }),
                            }
                            continue

                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content")
                        if content:
                            model_id = chunk.get("model", self.model_name)
                            yield {
                                "text": content,
                                "model": f"Answered by {model_id}",
                            }

        except httpx.HTTPStatusError as exc:
            logger.error(
                "LiteLLM stream failed [%s]: %s — %s",
                self.model_name,
                exc.response.status_code,
                exc.response.text,
            )
            raise
        except httpx.RequestError as exc:
            logger.error(
                "Network error during LiteLLM stream [%s]: %s",
                self.model_name,
                exc,
            )
            raise
