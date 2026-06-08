import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from infrastructure.database import Base
from infrastructure.models import (
    WorkspaceModel,
    AgentMemoryModel,
    ResearchTaskModel,
    TokenUsageLogModel,
    UserModel,
    MessageModel,
    ConversationModel
)

TEST_DB_URL = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/research_assistant"

@pytest.fixture
async def async_session():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    async with SessionLocal() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.mark.asyncio
async def test_workspace_has_active_model_version(async_session):
    workspace = WorkspaceModel(
        id=str(uuid.uuid4()),
        name="Test Workspace",
        active_model_version="research-agent:v2"
    )
    async_session.add(workspace)
    await async_session.commit()
    
    assert workspace.active_model_version == "research-agent:v2"

@pytest.mark.asyncio
async def test_agent_memory_model(async_session):
    workspace = WorkspaceModel(id=str(uuid.uuid4()), name="WS")
    async_session.add(workspace)
    await async_session.commit()
    
    memory = AgentMemoryModel(
        id=str(uuid.uuid4()),
        workspace_id=workspace.id,
        memory_key="user_preferences",
        memory_value={"theme": "dark", "level": 4}
    )
    async_session.add(memory)
    await async_session.commit()
    
    assert memory.memory_value["theme"] == "dark"

@pytest.mark.asyncio
async def test_research_task_model(async_session):
    user = UserModel(id=str(uuid.uuid4()), name="User", email="test@test.com")
    workspace = WorkspaceModel(id=str(uuid.uuid4()), name="WS")
    async_session.add_all([user, workspace])
    await async_session.commit()
    
    task = ResearchTaskModel(
        id="workflow-123",
        workspace_id=workspace.id,
        user_id=user.id,
        status="QUEUED",
        question="What is TDD?",
        tool_calls=[{"name": "search", "args": "TDD"}]
    )
    async_session.add(task)
    await async_session.commit()
    
    assert task.status == "QUEUED"
    assert task.tool_calls[0]["name"] == "search"

@pytest.mark.asyncio
async def test_token_usage_log_model(async_session):
    user = UserModel(id=str(uuid.uuid4()), name="User", email="test2@test.com")
    workspace = WorkspaceModel(id=str(uuid.uuid4()), name="WS")
    async_session.add_all([user, workspace])
    await async_session.commit()
    
    log = TokenUsageLogModel(
        id=str(uuid.uuid4()),
        workspace_id=workspace.id,
        user_id=user.id,
        model="gpt-4o",
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150
    )
    async_session.add(log)
    await async_session.commit()
    
    assert log.total_tokens == 150

@pytest.mark.asyncio
async def test_message_tool_calls(async_session):
    user = UserModel(id=str(uuid.uuid4()), name="User", email="test3@test.com")
    workspace = WorkspaceModel(id=str(uuid.uuid4()), name="WS")
    async_session.add_all([user, workspace])
    await async_session.commit()
    
    conv = ConversationModel(id=str(uuid.uuid4()), workspace_id=workspace.id, created_by=user.id)
    async_session.add(conv)
    await async_session.commit()
    
    msg = MessageModel(
        id=str(uuid.uuid4()),
        conversation_id=conv.id,
        role="assistant",
        content="Thinking...",
        tool_calls=[{"function": "search", "result": "found"}]
    )
    async_session.add(msg)
    await async_session.commit()
    
    assert msg.tool_calls[0]["function"] == "search"
