"""DSPy ReAct agent adapter — AI agent with Wikipedia search and file memory tools.

Implements :class:`IAgentProvider` using DSPy's ReAct module.
The agent reasons about which tools to use, acts, observes results,
and repeats until it produces a final answer.

Tools:
    - web_search: Look up factual information via the web.
    - remember_fact: Store a key-value fact in a JSON file.
    - recall_fact: Retrieve a previously stored fact by key.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

import dspy

from config import settings
from domain.ports.agent_port import IAgentProvider
from domain.value_objects.agent_result import AgentResult, ToolCallRecord

logger = logging.getLogger(__name__)

import contextvars
from tavily import TavilyClient
_current_workspace_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("_current_workspace_id", default=None)

# ── Memory file helpers ───────────────────────────────────────────────────


def _load_memory(path: str) -> dict[str, str]:
    """Load the memory JSON file, returning an empty dict if missing."""
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load agent memory from %s: %s", path, exc)
    return {}


def _save_memory(path: str, memory: dict[str, str]) -> None:
    """Save the memory dict to the JSON file."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)


# ── Tool functions ────────────────────────────────────────────────────────


def web_search(query: str) -> str:
    """Search the web for factual information.

    Args:
        query: The search query to look up on the web.

    Returns:
        A summary of the most relevant search results,
        or an error message if the search fails.
    """
    import logging
    from config import settings
    
    if not settings.TAVILY_API_KEY:
        return "Tavily API key is not configured. Web search is unavailable."
        
    try:
        client = TavilyClient(api_key=settings.TAVILY_API_KEY)
        response = client.search(query=query, search_depth="basic", max_results=3)
        
        if not response.get("results"):
            return f"No search results found for '{query}'."
            
        results_text = []
        for result in response["results"]:
            title = result.get("title", "")
            content = result.get("content", "")
            if title and content:
                results_text.append(f"[{title}] {content}")
                
        return "\\n".join(results_text)
    except Exception as exc:
        logging.getLogger(__name__).warning("Tavily search failed for query '%s': %s", query, exc)
        return f"Web search error: {str(exc)}"


def remember_fact(key: str, value: str) -> str:
    """Store a fact in the agent's persistent memory.

    Args:
        key: A short label or topic for the fact (e.g., 'capital of France').
        value: The fact to remember (e.g., 'Paris').

    Returns:
        Confirmation that the fact was stored.
    """
    workspace_id = _current_workspace_id.get() or "default"
    import asyncio
    from infrastructure.database import async_session_factory
    from adapters.repositories.agent_memory_repository import SqlAlchemyAgentMemoryRepository
    
    async def _do():
        async with async_session_factory() as session:
            repo = SqlAlchemyAgentMemoryRepository(session)
            await repo.remember(workspace_id, key, value)
            await session.commit()
    
    asyncio.run(_do())
    return f"Stored: '{key}' = '{value}'"


def recall_fact(key: str) -> str:
    """Retrieve a previously stored fact from the agent's memory.

    Args:
        key: The label or topic to look up in memory.

    Returns:
        The stored value, or a message indicating nothing was found.
    """
    workspace_id = _current_workspace_id.get() or "default"
    import asyncio
    from infrastructure.database import async_session_factory
    from adapters.repositories.agent_memory_repository import SqlAlchemyAgentMemoryRepository
    
    async def _do() -> str | None:
        async with async_session_factory() as session:
            repo = SqlAlchemyAgentMemoryRepository(session)
            return await repo.recall(workspace_id, key)
    
    result = asyncio.run(_do())
    if result:
        return result
        
    return f"No memory found for '{key}'."


# ── DSPy Agent Adapter ───────────────────────────────────────────────────


class DSPyAgentAdapter(IAgentProvider):
    """AI agent backed by DSPy ReAct with Web search and file memory.

    Parameters
    ----------
    model_name : str
        LiteLLM model alias (e.g., ``gemini-flash``, ``nova-lite``).
    litellm_base_url : str
        Root URL of the LiteLLM proxy (e.g., ``http://localhost:4000``).
    api_key : str
        LiteLLM API key for authentication.
    max_iters : int
        Maximum number of ReAct reasoning iterations.
    """

    def __init__(
        self,
        model_name: str = "gemini-flash",
        litellm_base_url: str | None = None,
        api_key: str | None = None,
        max_iters: int = 5,
        source_page: str = "agent",
    ) -> None:
        self.model_name = model_name
        self.litellm_base_url = (litellm_base_url or settings.LITELLM_BASE_URL).rstrip("/")
        self.api_key = api_key or settings.LITELLM_MASTER_KEY
        self.max_iters = max_iters
        self.source_page = source_page

        # Build DSPy tools
        self._tools = [
            dspy.Tool(web_search, name="web_search", desc="Search the web for factual information about any topic."),
            dspy.Tool(remember_fact, name="remember_fact", desc="Store a fact in persistent memory. Use key=topic and value=fact."),
            dspy.Tool(recall_fact, name="recall_fact", desc="Retrieve a previously stored fact from memory by its key/topic."),
        ]

    def _configure_lm(self) -> dspy.LM:
        """Configure and return a DSPy LM pointing at the LiteLLM proxy."""
        lm = dspy.LM(
            model=f"openai/{self.model_name}",
            api_base=f"{self.litellm_base_url}/v1",
            api_key=self.api_key,
            max_tokens=1024,
            temperature=0.7,
            extra_headers={"x-litellm-metadata": json.dumps({"source_page": self.source_page})},
        )
        return lm

    def _build_agent(self) -> dspy.ReAct:
        """Create a DSPy ReAct agent with the registered tools."""
        agent = dspy.ReAct(
            "question -> answer",
            tools=self._tools,
            max_iters=self.max_iters,
        )
        return agent

    def _extract_tool_calls(self, prediction: Any) -> list[ToolCallRecord]:
        """Extract tool call records from a DSPy ReAct prediction.

        DSPy ReAct stores its trajectory in the prediction object.
        We inspect it to find tool invocations and their results.
        """
        tool_calls: list[ToolCallRecord] = []

        try:
            # DSPy ReAct stores trajectory in prediction.trajectory
            trajectory = getattr(prediction, "trajectory", {})

            if isinstance(trajectory, dict):
                i = 0
                while True:
                    # ReAct trajectory keys: tool_name_{i}, tool_args_{i}, observation_{i}
                    tool_name_key = f"tool_name_{i}"
                    tool_args_key = f"tool_args_{i}"
                    obs_key = f"observation_{i}"

                    if tool_name_key not in trajectory:
                        break

                    tool_name = str(trajectory.get(tool_name_key, "unknown"))
                    tool_args = trajectory.get(tool_args_key, {})
                    observation = str(trajectory.get(obs_key, ""))

                    # Format the input for display
                    if isinstance(tool_args, dict):
                        input_str = json.dumps(tool_args, ensure_ascii=False)
                    else:
                        input_str = str(tool_args)

                    # Skip the "finish" action
                    if tool_name.lower() not in ("finish", "none", ""):
                        tool_calls.append(
                            ToolCallRecord(
                                tool=tool_name,
                                input=input_str,
                                output=observation,
                            )
                        )

                    i += 1

        except Exception as exc:
            logger.warning("Failed to extract tool calls from prediction: %s", exc)

        return tool_calls

    def _extract_thoughts(self, prediction: Any) -> list[str]:
        """Extract reasoning thoughts from a DSPy ReAct prediction trajectory."""
        thoughts: list[str] = []
        try:
            # DSPy ReAct stores trajectory in prediction.trajectory
            trajectory = getattr(prediction, "trajectory", {})

            if isinstance(trajectory, dict):
                i = 0
                while True:
                    thought_key = f"thought_{i}"
                    next_thought_key = f"next_thought_{i}"
                    rationale_key = f"rationale_{i}"

                    found_thought = None
                    if thought_key in trajectory:
                        found_thought = str(trajectory[thought_key])
                    elif next_thought_key in trajectory:
                        found_thought = str(trajectory[next_thought_key])
                    elif rationale_key in trajectory:
                        found_thought = str(trajectory[rationale_key])

                    tool_name_key = f"tool_name_{i}"
                    if not found_thought and tool_name_key not in trajectory:
                        break

                    if found_thought:
                        cleaned = found_thought.strip()
                        if cleaned.lower().startswith("thought:"):
                            cleaned = cleaned[len("thought:"):].strip()
                        if cleaned:
                            thoughts.append(cleaned)

                    i += 1

        except Exception as exc:
            logger.warning("Failed to extract thoughts from prediction: %s", exc)

        return thoughts

    async def run(
        self,
        question: str,
        user_id: str | None = None,
        workspace_id: str | None = None,
    ) -> AgentResult:
        """Run the DSPy ReAct agent on the given question.

        The agent is executed in a thread pool to avoid blocking
        the async event loop (DSPy's internals are synchronous).
        """
        _current_workspace_id.set(workspace_id)
        
        # Check if an optimized model is loaded from MLflow
        optimized_model = None
        try:
            from api.routes.agent import _OPTIMIZED_MODEL
            optimized_model = _OPTIMIZED_MODEL
        except Exception:
            pass

        lm = self._configure_lm()

        if optimized_model is not None:
            logger.info("Executing optimized model from MLflow Model Registry.")
            def _run_optimized_sync() -> tuple[str, list[ToolCallRecord], str, list[str]]:
                with dspy.context(lm=lm):
                    # Bind active LM to loaded model's submodules
                    try:
                        for p in optimized_model.predictors():
                            p.lm = lm
                    except Exception:
                        pass
                    prediction = optimized_model(question=question)

                answer = getattr(prediction, "answer", str(prediction))
                tool_calls = self._extract_tool_calls(prediction)
                thoughts = self._extract_thoughts(prediction)
                
                from api.routes.agent import _MODEL_INFO
                model_used = f"{_MODEL_INFO.get('model_name', self.model_name)} (registry v{_MODEL_INFO.get('version', 'unknown')})"

                return answer, tool_calls, model_used, thoughts

            import contextvars
            ctx = contextvars.copy_context()
            loop = asyncio.get_event_loop()
            answer, tool_calls, model_used, thoughts = await loop.run_in_executor(
                None, ctx.run, _run_optimized_sync
            )
        else:
            agent = self._build_agent()

            def _run_sync() -> tuple[str, list[ToolCallRecord], str, list[str]]:
                with dspy.context(lm=lm):
                    prediction = agent(question=question)

                answer = getattr(prediction, "answer", str(prediction))
                tool_calls = self._extract_tool_calls(prediction)
                thoughts = self._extract_thoughts(prediction)
                model_used = self.model_name

                return answer, tool_calls, model_used, thoughts

            # Run synchronous DSPy code in a thread pool
            import contextvars
            ctx = contextvars.copy_context()
            loop = asyncio.get_event_loop()
            answer, tool_calls, model_used, thoughts = await loop.run_in_executor(
                None, ctx.run, _run_sync
            )

        return AgentResult(
            answer=answer,
            tool_calls=tool_calls,
            model_used=model_used,
            thoughts=thoughts,
        )

