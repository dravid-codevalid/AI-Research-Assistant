import asyncio
import logging
import uuid
import sys
import os
from datetime import datetime, timezone

# Add backend directory to sys.path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine
from config import settings
from infrastructure.database import Base
import infrastructure.models as _models
from api.auth_utils import get_password_hash
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("reset_db")

async def reset_db():
    DATABASE_URL = settings.APP_DATABASE_URL
    logger.info(f"Resetting database at {DATABASE_URL}...")
    
    engine = create_async_engine(DATABASE_URL, echo=False)
    
    # Drop and recreate all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    # Seed default user and workspace
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        # Seed Admin user
        admin_pw = get_password_hash("Dravid@admin")
        admin_user = _models.UserModel(
            id="admin-user-id", # fixed ID for E2E tests
            name="Admin User",
            email="codevalid-admin",
            hashed_password=admin_pw,
            is_admin=True,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        session.add(admin_user)
        
        # Seed normal user
        normal_pw = get_password_hash("password123")
        normal_user = _models.UserModel(
            id="test-user-id", # fixed ID for E2E tests
            name="Test User",
            email="test@example.com",
            hashed_password=normal_pw,
            is_admin=False,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        session.add(normal_user)

        # Seed Workspace
        workspace = _models.WorkspaceModel(
            id="workspace-id-1", # fixed ID for E2E tests
            name="Research Lab",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        session.add(workspace)
        
        await session.commit()
        
        # Add normal user as workspace member
        membership = _models.UserWorkspaceModel(
            user_id="test-user-id",
            workspace_id="workspace-id-1",
            role="member"
        )
        session.add(membership)
        await session.commit()
        
    await engine.dispose()
    logger.info("Database reset and seeded successfully!")

if __name__ == "__main__":
    asyncio.run(reset_db())
