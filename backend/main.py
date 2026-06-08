"""AI Research Assistant — FastAPI application entry point."""

import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI

from api.middleware import setup_middleware
from api.routes.agent import router as agent_router
from api.routes.auth import router as auth_router
from api.routes.ask import router as ask_router
from api.routes.conversations import router as conversations_router
from api.routes.health import router as health_router
from api.routes.usage import router as usage_router
from api.routes.users import router as users_router
from api.routes.workspaces import router as workspaces_router
from api.routes.workflows import router as workflows_router
from api.routes.feedback import router as feedback_router
from api.auth_utils import get_password_hash
from config import settings
from infrastructure.database import async_session_factory, create_tables
from adapters.repositories.user_repository import SqlAlchemyUserRepository
from adapters.repositories.workspace_repository import SqlAlchemyWorkspaceRepository
from domain.entities.user import User
from domain.entities.workspace import Workspace

logger = logging.getLogger(__name__)


# ── Seed data ─────────────────────────────────────────────────────────────

async def _seed_data() -> None:
    """Create initial dev users and workspaces if the DB is empty."""
    async with async_session_factory() as session:
        user_repo = SqlAlchemyUserRepository(session)
        ws_repo = SqlAlchemyWorkspaceRepository(session)

        existing_users = await user_repo.list_all()
        if existing_users:
            return  # Already seeded

        logger.info("Seeding initial dev data…")

        admin_pw = get_password_hash("Dravid@admin")
        admin_user = User(
            id=str(uuid.uuid4()),
            name="Admin",
            email="codevalid-admin",
            hashed_password=admin_pw,
            is_admin=True,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        await user_repo.create(admin_user)

        # Workspaces
        lab = Workspace(
            id=str(uuid.uuid4()),
            name="Research Lab",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        await ws_repo.create(lab)

        await session.commit()
        logger.info("Seeded 1 admin user and 1 workspace.")


# ── Lifespan ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hooks."""
    # Startup
    await create_tables()
    await _seed_data()

    # Try to load MLflow optimized model in a background thread
    import asyncio
    from api.routes.agent import load_optimized_model
    asyncio.create_task(asyncio.to_thread(load_optimized_model))

    yield
    # Shutdown (nothing to clean up for now)


# ── Application ───────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "AI Research Assistant backend — Level 4: AI Agent with Tools. "
        "DSPy ReAct agent with Wikipedia search and file-based memory, "
        "multi-model routing via LiteLLM, User/Workspace hierarchy."
    ),
    version="0.4.0",
    lifespan=lifespan,
)

setup_middleware(app)

app.include_router(health_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(ask_router, prefix="/api")
app.include_router(agent_router, prefix="/api")
app.include_router(conversations_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(workspaces_router, prefix="/api")
app.include_router(usage_router, prefix="/api")
app.include_router(workflows_router, prefix="/api")
app.include_router(feedback_router, prefix="/api")


@app.get("/")
async def root() -> dict[str, str]:
    """Welcome message at the application root."""
    return {
        "message": (
            f"Welcome to {settings.APP_NAME}! "
            "Visit /docs for the interactive API documentation."
        )
    }
