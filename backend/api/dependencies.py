"""FastAPI dependency injection providers.

Supports three LLM provider modes controlled by config.LLM_PROVIDER:
  - "echo"    → Level 1 echo placeholder
  - "bedrock" → Level 2 direct AWS Bedrock
  - "litellm" → Level 3+ via LiteLLM proxy (default)
"""

import logging

from adapters.llm.bedrock_llm import BedrockLLM
from adapters.llm.echo_llm import EchoLLM
from adapters.llm.litellm_llm import LiteLLMLLM
from adapters.llm.model_registry import DEFAULT_MODEL_ID
from adapters.repositories.conversation_repository import SqlAlchemyConversationRepository
from adapters.repositories.workspace_repository import SqlAlchemyWorkspaceRepository
from config import settings
from domain.ports.llm_provider import ILLMProvider
from infrastructure.database import async_session_factory
from use_cases.ask_question import AskQuestionUseCase

logger = logging.getLogger(__name__)


def get_llm_provider(
    model_id: str = DEFAULT_MODEL_ID,
    user_id: str | None = None,
    workspace_id: str | None = None,
    litellm_api_key: str | None = None,
) -> ILLMProvider:
    """Provide the LLM provider based on the configured mode."""
    provider = settings.LLM_PROVIDER.lower()

    if provider == "litellm":
        # Use master key as fallback when no per-user key is available
        api_key = litellm_api_key or settings.LITELLM_MASTER_KEY
        return LiteLLMLLM(
            base_url=settings.LITELLM_BASE_URL,
            api_key=api_key,
            model_name=model_id,
        )
    elif provider == "bedrock":
        return BedrockLLM(model_id=model_id)
    else:
        return EchoLLM()


async def get_ask_use_case_for_model(
    model_id: str = DEFAULT_MODEL_ID,
    user_id: str | None = None,
    workspace_id: str | None = None,
) -> AskQuestionUseCase:
    """Provide the AskQuestionUseCase wired to the appropriate LLM provider and conversation repo.

    Creates a new database session for the conversation repository.
    The session is managed by the use case's lifecycle.
    """
    # Look up the user's per-workspace LiteLLM key if both IDs are provided
    litellm_api_key: str | None = None
    if user_id and workspace_id:
        try:
            async with async_session_factory() as lookup_session:
                ws_repo = SqlAlchemyWorkspaceRepository(lookup_session)
                membership = await ws_repo.get_membership(user_id, workspace_id)
                if membership and membership.litellm_key:
                    litellm_api_key = membership.litellm_key
                    logger.debug(
                        "Using per-user LiteLLM key for user '%s' in workspace '%s'",
                        user_id, workspace_id,
                    )
        except Exception:
            logger.warning(
                "Failed to look up LiteLLM key for user '%s' — falling back to master key.",
                user_id,
            )

    llm = get_llm_provider(
        model_id=model_id,
        user_id=user_id,
        workspace_id=workspace_id,
        litellm_api_key=litellm_api_key,
    )
    # Create a session for the conversation repository
    session = async_session_factory()
    conversation_repo = SqlAlchemyConversationRepository(session)

    # Create use case — the session will be committed by the use case
    use_case = AskQuestionUseCase(
        llm_provider=llm,
        conversation_repo=conversation_repo,
    )
    # Attach session so it can be committed/closed
    use_case._session = session
    return use_case
