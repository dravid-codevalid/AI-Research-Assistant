"""Shared test fixtures for the backend test suite."""

import pytest
from unittest.mock import patch
from httpx import ASGITransport, AsyncClient

# --- Configure SQLite in-memory database for tests ---
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
import infrastructure.database

test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
test_session_factory = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Mutate the imported module's engine and session factory
infrastructure.database.async_engine = test_engine
infrastructure.database.async_session_factory = test_session_factory

from main import app
from adapters.llm.echo_llm import EchoLLM
from use_cases.ask_question import AskQuestionUseCase

# Build the mock function that dynamically creates the use case with a database session
async def _mock_get_ask_use_case_for_model(
    model_id: str = "echo",
    user_id: str | None = None,
    workspace_id: str | None = None,
) -> AskQuestionUseCase:
    """Always return the EchoLLM use case regardless of model_id."""
    from adapters.repositories.conversation_repository import SqlAlchemyConversationRepository
    from infrastructure.database import async_session_factory
    session = async_session_factory()
    repo = SqlAlchemyConversationRepository(session)
    use_case = AskQuestionUseCase(llm_provider=EchoLLM(), conversation_repo=repo)
    use_case._session = session
    return use_case


from domain.entities.user import User

async def mock_get_current_user() -> User:
    return User(
        id="test-user-id",
        name="Test User",
        email="test@example.com",
        is_admin=True,
        created_at="2026-06-04T10:00:00Z"
    )


@pytest.fixture(autouse=True)
def _override_auth():
    from api.auth_utils import get_current_user
    app.dependency_overrides[get_current_user] = mock_get_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture(autouse=True)
def _override_llm():
    """Patch the dependency factory so tests never hit AWS Bedrock."""
    with patch(
        "api.routes.ask.get_ask_use_case_for_model",
        _mock_get_ask_use_case_for_model,
    ):
        yield


@pytest.fixture
async def client() -> AsyncClient:
    """Create an async HTTP test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.fixture(autouse=True, scope="module")
async def _setup_db():
    """Ensure tables exist with the latest schema and the mock user is inserted.
    
    Uses module scope to ensure a clean database for each file, but preserve state
    for sequential tests in the same file.
    """
    from infrastructure.database import async_engine, Base
    import infrastructure.models as _models  # noqa: F401

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        
        # Insert the mock test user to satisfy Postgres foreign keys
        from sqlalchemy import text
        await conn.execute(
            text(
                "INSERT INTO users (id, name, email, is_admin, created_at) "
                "VALUES ('test-user-id', 'Test User', 'test@example.com', true, '2026-06-04T10:00:00Z')"
            )
        )
    yield


