"""Ask question use case — orchestrates sending a question to the LLM provider.

Supports conversation context by loading previous messages from the
database and passing them as history to the LLM. Also persists user
and assistant messages for future context.

The system prompt follows the Instruction Hierarchy pattern from the
prompt-engineering-patterns skill:
  [System Context] → [Task Instruction] → [Output Format] → [Error Recovery]
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from domain.entities.conversation import Conversation
from domain.entities.message import Message
from domain.ports.conversation_repository import IConversationRepository
from domain.ports.llm_provider import ILLMProvider
from domain.value_objects.answer import Answer

# ── System Prompt & Few-Shot Selection ──────────────────────────────────────
# Designed using the prompt engineering Instruction Hierarchy pattern:
#   1. System Context  — who the model is and its domain
#   2. Task Instruction — what the model should do
#   3. Examples        — dynamic few-shot examples selected via embeddings
#   4. Output Format   — response guidelines
#   5. Error Recovery   — handling uncertainty
#
# Best practices applied:
#   • Be specific (avoid vague instructions)
#   • Progressive disclosure (clear sections, increasing detail)
#   • Confidence calibration (acknowledge uncertainty)
#   • Token efficiency (concise but complete)

SYSTEM_PROMPT_TEMPLATE = """You are an AI Research Assistant — an expert at synthesizing information, explaining complex topics, and helping users accelerate their research.

## Your Capabilities
- Answer research questions with clarity, accuracy, and depth.
- Summarize complex topics into digestible explanations.
- Provide structured comparisons when multiple options or viewpoints exist.
- Cite reasoning and context so the user understands *why*, not just *what*.

## Response Guidelines
1. **Structure**: Use headings, bullet points, and numbered lists to organize longer answers. Short factual answers can be a single sentence.
2. **Accuracy**: Ground your answers in established knowledge. Distinguish between well-established facts and emerging research.
3. **Conciseness**: Be thorough but not verbose. Prioritize signal over noise.
4. **Code & Technical Content**: When providing code examples, use fenced code blocks with language identifiers. Explain non-obvious design choices.

{few_shots_section}

## Handling Uncertainty
- If you are unsure about a claim, say so explicitly: "I'm not fully certain, but…"
- If a question is ambiguous, ask a clarifying question before answering.
- Never fabricate citations, statistics, or specific data points."""


def select_few_shots(question: str, limit: int = 3) -> str:
    """Select the most semantically similar few-shot examples using cosine similarity on embeddings."""
    try:
        import os
        import json
        import numpy as np
        import litellm
        
        # Load precomputed examples
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        filepath = os.path.join(base_dir, "few_shot_examples.json")
        if not os.path.exists(filepath):
            return ""
            
        with open(filepath, "r", encoding="utf-8") as f:
            examples = json.load(f)
            
        if not examples:
            return ""
            
        # Get embedding of user's query
        api_key = os.environ.get("GEMINI_API_KEY")
        res = litellm.embedding(
            model="gemini/gemini-embedding-2",
            input=[question],
            api_key=api_key
        )
        query_vector = np.array(res["data"][0]["embedding"])
        
        # Compute cosine similarity
        similarities = []
        for ex in examples:
            if "embedding" not in ex:
                continue
            ex_vector = np.array(ex["embedding"])
            # Cosine similarity formula: (A . B) / (||A|| * ||B||)
            dot_product = np.dot(query_vector, ex_vector)
            norm_q = np.linalg.norm(query_vector)
            norm_ex = np.linalg.norm(ex_vector)
            sim = dot_product / (norm_q * norm_ex) if norm_q > 0 and norm_ex > 0 else 0.0
            similarities.append((sim, ex))
            
        # Sort by similarity descending
        similarities.sort(key=lambda x: x[0], reverse=True)
        top_examples = [item[1] for item in similarities[:limit]]
        
        # Format as string
        formatted_examples = []
        for i, ex in enumerate(top_examples, 1):
            formatted_examples.append(
                f"### Example {i}\n"
                f"**User Question**: {ex['question']}\n"
                f"**Assistant Response**: {ex['answer']}"
            )
            
        return "\n\n".join(formatted_examples)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Failed to select few-shot examples: %s", exc)
        return ""


# Maximum number of previous messages to include as context
MAX_HISTORY_MESSAGES = 20


class AskQuestionUseCase:
    """Use case for asking a question to the LLM provider.

    Manages conversation lifecycle: creates conversations, persists
    messages, loads history for context, and tracks token usage.
    """

    def __init__(
        self,
        llm_provider: ILLMProvider,
        conversation_repo: IConversationRepository,
    ) -> None:
        self.llm_provider = llm_provider
        self.conversation_repo = conversation_repo

    def _generate_title(self, question: str) -> str:
        """Generate a conversation title from the first user message."""
        title = question.strip()
        if len(title) > 50:
            title = title[:47] + "..."
        return title

    async def _get_or_create_conversation(
        self,
        conversation_id: str | None,
        user_id: str | None,
        workspace_id: str | None,
        question: str,
    ) -> tuple[str, bool]:
        """Return (conversation_id, is_new). Creates a new conversation if needed."""
        if conversation_id:
            existing = await self.conversation_repo.get_conversation_by_id(
                conversation_id
            )
            if existing:
                return conversation_id, False

        # Create a new conversation
        new_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        conversation = Conversation(
            id=new_id,
            workspace_id=workspace_id,
            created_by=user_id,
            title=self._generate_title(question),
            created_at=now,
            updated_at=now,
        )
        await self.conversation_repo.create_conversation(conversation)
        return new_id, True

    async def _load_history(
        self, conversation_id: str
    ) -> list[dict[str, str]]:
        """Load the last N messages from the DB as chat history."""
        messages = await self.conversation_repo.get_messages(
            conversation_id, limit=MAX_HISTORY_MESSAGES
        )
        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

    async def _save_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        model: str | None = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
    ) -> Message:
        """Persist a message to the database."""
        message = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role=role,
            content=content,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        saved = await self.conversation_repo.add_message(message)
        # Update conversation timestamp
        await self.conversation_repo.update_conversation_timestamp(conversation_id)
        return saved

    # ── One-shot execution ─────────────────────────────────────────────

    async def execute(
        self,
        question: str,
        user_id: str | None = None,
        workspace_id: str | None = None,
        conversation_id: str | None = None,
    ) -> tuple[Answer, str]:
        """Execute the ask-question use case.

        Args:
            question: The user's question text.
            user_id: Optional user ID for spend tracking.
            workspace_id: Optional workspace ID for spend tracking.
            conversation_id: Optional existing conversation ID.

        Returns:
            A tuple of (Answer, conversation_id).

        Raises:
            ValueError: If the question is empty or whitespace-only.
        """
        try:
            if not question or not question.strip():
                raise ValueError("Question must not be empty.")

            # Get or create conversation
            conv_id, _is_new = await self._get_or_create_conversation(
                conversation_id, user_id, workspace_id, question
            )

            # Load conversation history from DB
            history = await self._load_history(conv_id)

             # Save user message
            await self._save_message(conv_id, "user", question.strip())

            # Commit the session immediately so the user message is saved
            if hasattr(self, '_session'):
                await self._session.commit()

            # Select few-shot examples and render system prompt
            few_shots = select_few_shots(question.strip())
            few_shots_section = ""
            if few_shots:
                few_shots_section = (
                    "## Example Q&A Demonstrations\n"
                    "Use the following examples to guide your response structure, level of depth, and formatting:\n\n"
                    f"{few_shots}"
                )
            rendered_prompt = SYSTEM_PROMPT_TEMPLATE.format(few_shots_section=few_shots_section)

            # Call LLM with history
            answer = await self.llm_provider.ask(
                question,
                system_prompt=rendered_prompt,
                messages=history,
                user_id=user_id,
                workspace_id=workspace_id,
            )

            # Save assistant response with token counts
            await self._save_message(
                conv_id,
                "assistant",
                answer.text,
                model=answer.model,
                prompt_tokens=answer.prompt_tokens,
                completion_tokens=answer.completion_tokens,
                total_tokens=answer.total_tokens,
            )

            # Log token usage to DB
            if workspace_id and user_id:
                try:
                    model_cleaned = answer.model
                    if model_cleaned and model_cleaned.startswith("Answered by "):
                        model_cleaned = model_cleaned[len("Answered by "):]
                    
                    await self.conversation_repo.log_token_usage(
                        workspace_id=workspace_id,
                        user_id=user_id,
                        model=model_cleaned or "unknown",
                        prompt_tokens=answer.prompt_tokens,
                        completion_tokens=answer.completion_tokens,
                        total_tokens=answer.total_tokens,
                        cost=None,
                    )
                except Exception as log_exc:
                    import logging
                    logging.getLogger(__name__).warning("Failed to log token usage: %s", log_exc)

            # Commit the session
            if hasattr(self, '_session'):
                await self._session.commit()

            return answer, conv_id
        finally:
            if hasattr(self, '_session'):
                await self._session.close()

    # ── Streaming execution ────────────────────────────────────────────

    async def execute_stream(
        self,
        question: str,
        user_id: str | None = None,
        workspace_id: str | None = None,
        conversation_id: str | None = None,
    ):
        """Execute the ask-question use case incrementally.

        Yields dicts with 'text', 'model', and optionally 'conversation_id' keys.
        The first chunk always includes 'conversation_id'.
        """
        try:
            if not question or not question.strip():
                raise ValueError("Question must not be empty.")

            # Get or create conversation
            conv_id, _is_new = await self._get_or_create_conversation(
                conversation_id, user_id, workspace_id, question
            )

            # Load conversation history from DB
            history = await self._load_history(conv_id)

             # Save user message
            await self._save_message(conv_id, "user", question.strip())

            # Commit the session immediately so the user message is saved
            if hasattr(self, '_session'):
                await self._session.commit()

            # Select few-shot examples and render system prompt
            few_shots = select_few_shots(question.strip())
            few_shots_section = ""
            if few_shots:
                few_shots_section = (
                    "## Example Q&A Demonstrations\n"
                    "Use the following examples to guide your response structure, level of depth, and formatting:\n\n"
                    f"{few_shots}"
                )
            rendered_prompt = SYSTEM_PROMPT_TEMPLATE.format(few_shots_section=few_shots_section)

            # Stream LLM response with history
            full_response = ""
            model_name = ""
            prompt_tokens = 0
            completion_tokens = 0
            total_tokens = 0
            first_chunk = True

            async for chunk in self.llm_provider.ask_stream(
                question,
                system_prompt=rendered_prompt,
                messages=history,
                user_id=user_id,
                workspace_id=workspace_id,
            ):
                # Check for usage metadata chunk
                if "usage" in chunk:
                    try:
                        usage_data = json.loads(chunk["usage"])
                        prompt_tokens = usage_data.get("prompt_tokens", 0)
                        completion_tokens = usage_data.get("completion_tokens", 0)
                        total_tokens = usage_data.get("total_tokens", 0)
                    except (json.JSONDecodeError, TypeError):
                        pass
                    continue

                text = chunk.get("text", "")
                model = chunk.get("model", "")
                if model:
                    model_name = model
                full_response += text

                out: dict[str, str] = {"text": text, "model": model}
                if first_chunk:
                    out["conversation_id"] = conv_id
                    first_chunk = False

                yield out

            # Save assistant response with token counts
            await self._save_message(
                conv_id,
                "assistant",
                full_response,
                model=model_name or None,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            )

            # Log token usage to DB
            if workspace_id and user_id:
                try:
                    await self.conversation_repo.log_token_usage(
                        workspace_id=workspace_id,
                        user_id=user_id,
                        model=model_name or "unknown",
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens,
                        cost=None,
                    )
                except Exception as log_exc:
                    import logging
                    logging.getLogger(__name__).warning("Failed to log token usage: %s", log_exc)

            # Commit the session
            if hasattr(self, '_session'):
                await self._session.commit()
        finally:
            if hasattr(self, '_session'):
                await self._session.close()
