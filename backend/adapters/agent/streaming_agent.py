from __future__ import annotations

import asyncio
import json
import logging
import httpx
from collections.abc import AsyncGenerator
from typing import Any

from domain.ports.agent_port import IAgentProvider
from domain.value_objects.agent_result import AgentResult, ToolCallRecord
from config import settings
from adapters.agent.dspy_agent import web_search, remember_fact, recall_fact

logger = logging.getLogger(__name__)

# Maximum characters to keep from a tool observation before truncating.
MAX_OBSERVATION_LENGTH = 2000

# System prompt — clean and focused. Tool details are conveyed via the
# structured `tools` parameter, so the prompt only needs behavioral guidance.
SYSTEM_PROMPT = """You are a Research Assistant. Your job is to answer research questions accurately and concisely.

You have access to tools that let you search the web, store facts in persistent memory, and recall previously stored facts.

Guidelines:
- First, check memory via recall_fact for any key terms or labels related to the question before calling other tools.
- Use web_search only if the required information is missing or incomplete in memory.
- Use remember_fact to store important findings for future reference. Do not save duplicates.
- Think step-by-step before answering.
- If you can answer directly from knowledge or memory, do so without searching the web.
- Always provide a clear, well-structured final answer.
"""


# OpenAI-compatible tool definitions sent with every LiteLLM request.
TOOLS_SCHEMA: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for factual information about any topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to look up on the web.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remember_fact",
            "description": "Store a fact in persistent memory. Use key as the topic and value as the fact.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "The topic or label for this fact.",
                    },
                    "value": {
                        "type": "string",
                        "description": "The fact to store.",
                    },
                },
                "required": ["key", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recall_fact",
            "description": "Retrieve a previously stored fact from memory by its key/topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "The topic or label to look up.",
                    }
                },
                "required": ["key"],
            },
        },
    },
]

# Maps tool names to their callable implementations.
TOOL_REGISTRY: dict[str, Any] = {
    "web_search": lambda args: web_search(args["query"]),
    "remember_fact": lambda args: remember_fact(args["key"], args["value"]),
    "recall_fact": lambda args: recall_fact(args["key"]),
}


def _truncate(text: str, max_len: int = MAX_OBSERVATION_LENGTH) -> str:
    """Truncate a string to *max_len* characters, appending an ellipsis indicator."""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "\n... [truncated]"


class StreamingLiteLLMAgent(IAgentProvider):
    """Streaming agent that uses native LLM function calling via the LiteLLM proxy.

    Strategy:
    - Tool-calling iterations use non-streaming requests (avoids LiteLLM/Gemini
      streaming+tools incompatibility) and emit thought/tool_call events.
    - The final answer iteration uses streaming to deliver tokens in real-time.
    """

    def __init__(
        self,
        model_name: str = "gemini-flash",
        base_url: str | None = None,
        api_key: str | None = None,
        max_iters: int = 5,
        source_page: str = "agent",
    ) -> None:
        self.model_name = model_name
        self.base_url = (base_url or settings.LITELLM_BASE_URL).rstrip("/")
        self.api_key = api_key or settings.LITELLM_MASTER_KEY
        self.max_iters = max_iters
        self.source_page = source_page

    def _build_headers(self, user_id: str | None, workspace_id: str | None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if user_id:
            headers["x-litellm-user-id"] = user_id
        if workspace_id:
            headers["x-litellm-team-id"] = workspace_id
        return headers

    def _execute_tool(self, tool_name: str, tool_args_str: str) -> str:
        """Parse JSON arguments and execute the named tool."""
        try:
            args = json.loads(tool_args_str) if tool_args_str else {}
            executor = TOOL_REGISTRY.get(tool_name)
            if executor:
                return executor(args)
            return f"Error: Tool '{tool_name}' not found."
        except json.JSONDecodeError:
            return f"Error: Could not parse tool arguments: {tool_args_str}"
        except Exception as e:
            return f"Error executing tool: {str(e)}"

    # ── Streaming entry point ─────────────────────────────────────────────

    async def run_stream(
        self,
        question: str,
        user_id: str | None = None,
        workspace_id: str | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Run the agent with native function calling, yielding streaming events.

        Yields events:
        - {"event": "thought", "text": "..."}
        - {"event": "tool_call", "tool": "...", "input": "...", "output": "..."}
        - {"event": "token", "text": "...", "model_used": "..."}
        - {"event": "done", "answer": "...", "tool_calls": [...], "thoughts": [...]}
        """
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]

        thoughts: list[str] = []
        tool_calls_record: list[dict[str, str]] = []
        final_answer = ""
        model_used = self.model_name
        total_prompt_tokens = 0
        total_completion_tokens = 0

        # Bind workspace context for memory tools
        from adapters.agent import dspy_agent
        dspy_agent._current_workspace_id.set(workspace_id)

        headers = self._build_headers(user_id, workspace_id)

        for iteration in range(self.max_iters):
            logger.info("Function-calling iteration %d starting", iteration)

            # ── Non-streaming call with tools ─────────────────────────
            payload: dict[str, Any] = {
                "model": self.model_name,
                "messages": messages,
                "tools": TOOLS_SCHEMA,
                "stream": False,
                "temperature": 0.0,
                "metadata": {"source_page": self.source_page},
            }

            try:
                max_retries = 3
                result = None
                for attempt in range(max_retries):
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        response = await client.post(
                            f"{self.base_url}/v1/chat/completions",
                            headers=headers,
                            json=payload,
                        )
                        if response.status_code == 429 and attempt < max_retries - 1:
                            wait = 2 ** (attempt + 1)  # 2s, 4s
                            logger.warning("Rate limited (429), retrying in %ds (attempt %d/%d)", wait, attempt + 1, max_retries)
                            yield {"event": "thought", "text": f"Rate limited, retrying in {wait}s..."}
                            await asyncio.sleep(wait)
                            continue
                        response.raise_for_status()
                        result = response.json()
                        break
            except Exception as exc:
                logger.error("Error in agent completions call: %s", exc)
                yield {"event": "error", "text": f"LLM error: {str(exc)}"}
                return

            choice = result.get("choices", [{}])[0]
            message = choice.get("message", {})
            finish_reason = choice.get("finish_reason", "")
            content = message.get("content", "") or ""
            response_tool_calls = message.get("tool_calls")

            # Accumulate token usage
            usage = result.get("usage") or {}
            total_prompt_tokens += usage.get("prompt_tokens", 0) or 0
            total_completion_tokens += usage.get("completion_tokens", 0) or 0

            # Track which model actually answered (may differ due to fallbacks)
            model_used = result.get("model", self.model_name)

            # ── Case 1: Model wants to call tools ─────────────────────
            if response_tool_calls:
                # Emit any reasoning text the model produced alongside tool calls
                if content.strip():
                    thoughts.append(content.strip())
                    yield {"event": "thought", "text": content.strip()}

                # Build the assistant message for the conversation history
                assistant_message: dict[str, Any] = {
                    "role": "assistant",
                    "content": content or None,
                    "tool_calls": response_tool_calls,
                }
                messages.append(assistant_message)

                # Execute each tool call
                for tc in response_tool_calls:
                    fn = tc.get("function", {})
                    tool_name = fn.get("name", "unknown")
                    tool_args_str = fn.get("arguments", "{}")
                    tool_call_id = tc.get("id", "")

                    logger.info("Executing tool: %s with args: %s", tool_name, tool_args_str)

                    # Emit a thought about the tool being called
                    thought_text = f"Calling {tool_name}..."
                    thoughts.append(thought_text)
                    yield {"event": "thought", "text": thought_text}

                    observation = await asyncio.to_thread(self._execute_tool, tool_name, tool_args_str)

                    # Full output for frontend, truncated for context history
                    truncated_observation = _truncate(observation)

                    tc_record = {
                        "tool": tool_name,
                        "input": tool_args_str,
                        "output": observation,
                    }
                    tool_calls_record.append(tc_record)
                    yield {
                        "event": "tool_call",
                        "tool": tool_name,
                        "input": tool_args_str,
                        "output": observation,
                    }

                    # Append tool result to conversation history
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": truncated_observation,
                    })

                # Continue the loop for the next iteration
                continue

            # ── Case 2: Model produced a final text answer ────────────
            # Chunk and yield the final answer text content to simulate streaming
            # without re-issuing a second API request.
            final_answer = content.strip()
            chunk_size = 12
            for i in range(0, len(final_answer), chunk_size):
                chunk_text = final_answer[i:i+chunk_size]
                yield {"event": "token", "text": chunk_text, "model_used": model_used}
                await asyncio.sleep(0.01)

            break  # We have the final answer, exit the loop

        yield {
            "event": "done",
            "answer": final_answer.strip(),
            "tool_calls": tool_calls_record,
            "thoughts": thoughts,
            "model_used": model_used,
            "prompt_tokens": total_prompt_tokens,
            "completion_tokens": total_completion_tokens,
            "total_tokens": total_prompt_tokens + total_completion_tokens,
        }

    # ── Non-streaming convenience method ──────────────────────────────────

    async def run(
        self,
        question: str,
        user_id: str | None = None,
        workspace_id: str | None = None,
    ) -> AgentResult:
        """Run the agent to completion and return an AgentResult."""
        answer = ""
        tool_calls: list[ToolCallRecord] = []
        thoughts: list[str] = []
        model_used = self.model_name
        prompt_tokens = 0
        completion_tokens = 0

        async for event in self.run_stream(question, user_id, workspace_id):
            if event["event"] == "error":
                raise Exception(event.get("text", "Unknown LLM Error"))
            elif event["event"] == "done":
                answer = event["answer"]
                tool_calls = [
                    ToolCallRecord(tool=tc["tool"], input=tc["input"], output=tc["output"])
                    for tc in event["tool_calls"]
                ]
                thoughts = event["thoughts"]
                model_used = event.get("model_used", self.model_name)
                prompt_tokens = event.get("prompt_tokens", 0)
                completion_tokens = event.get("completion_tokens", 0)

        return AgentResult(
            answer=answer,
            tool_calls=tool_calls,
            model_used=model_used,
            thoughts=thoughts,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )

