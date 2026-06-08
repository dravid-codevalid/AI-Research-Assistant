"""SQLAlchemy ORM models — mapped to the ``users``, ``workspaces``,
``user_workspaces``, ``conversations``, and ``messages`` tables."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint, Boolean, Integer, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database import Base


class UserModel(Base):
    """ORM model for the ``users`` table."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=lambda: datetime.now(timezone.utc).isoformat(),
    )

    # Relationships
    workspace_memberships: Mapped[list[UserWorkspaceModel]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<UserModel id={self.id!r} email={self.email!r}>"


class WorkspaceModel(Base):
    """ORM model for the ``workspaces`` table."""

    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=lambda: datetime.now(timezone.utc).isoformat(),
    )
    litellm_team_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, default=None
    )
    active_model_version: Mapped[str | None] = mapped_column(
        String(255), nullable=True, default=None
    )

    # Relationships
    members: Mapped[list[UserWorkspaceModel]] = relationship(
        back_populates="workspace",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<WorkspaceModel id={self.id!r} name={self.name!r}>"


class UserWorkspaceModel(Base):
    """ORM model for the ``user_workspaces`` join table."""

    __tablename__ = "user_workspaces"
    __table_args__ = (
        UniqueConstraint("user_id", "workspace_id", name="uq_user_workspace"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="member")
    litellm_key: Mapped[str | None] = mapped_column(
        String(512), nullable=True, default=None
    )

    # Relationships
    user: Mapped[UserModel] = relationship(back_populates="workspace_memberships")
    workspace: Mapped[WorkspaceModel] = relationship(back_populates="members")

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<UserWorkspaceModel user={self.user_id!r} "
            f"workspace={self.workspace_id!r} role={self.role!r}>"
        )


class ConversationModel(Base):
    """ORM model for the ``conversations`` table."""

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    created_by: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(500), nullable=False, default="New Conversation"
    )
    created_at: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=lambda: datetime.now(timezone.utc).isoformat(),
    )
    updated_at: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=lambda: datetime.now(timezone.utc).isoformat(),
    )

    # Relationships
    messages: Mapped[list["MessageModel"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="MessageModel.created_at",
    )
    workspace: Mapped[WorkspaceModel] = relationship()
    creator: Mapped[UserModel] = relationship()

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ConversationModel id={self.id!r} title={self.title!r}>"


class MessageModel(Base):
    """ORM model for the ``messages`` table."""

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    tool_calls: Mapped[list | dict | None] = mapped_column(JSON, nullable=True, default=None)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=lambda: datetime.now(timezone.utc).isoformat(),
    )

    # Relationships
    conversation: Mapped[ConversationModel] = relationship(back_populates="messages")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<MessageModel id={self.id!r} role={self.role!r}>"


class AgentMemoryModel(Base):
    """ORM model for the ``agent_memories`` table (Level 4)."""

    __tablename__ = "agent_memories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    memory_key: Mapped[str] = mapped_column(String(255), nullable=False)
    memory_value: Mapped[dict | list] = mapped_column(JSON, nullable=False)
    created_at: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=lambda: datetime.now(timezone.utc).isoformat(),
    )


class ResearchTaskModel(Base):
    """ORM model for the ``research_tasks`` table (Level 5)."""

    __tablename__ = "research_tasks"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)  # Temporal Workflow ID
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="QUEUED")
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    tool_calls: Mapped[list | dict | None] = mapped_column(JSON, nullable=True, default=None)
    created_at: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=lambda: datetime.now(timezone.utc).isoformat(),
    )
    updated_at: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=lambda: datetime.now(timezone.utc).isoformat(),
    )


class TokenUsageLogModel(Base):
    """ORM model for the ``token_usage_logs`` table (Levels 3 & 6)."""

    __tablename__ = "token_usage_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    created_at: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=lambda: datetime.now(timezone.utc).isoformat(),
    )


class FeedbackModel(Base):
    """ORM model for the ``feedbacks`` table."""

    __tablename__ = "feedbacks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    workspace_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="SET NULL"),
        nullable=True,
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=lambda: datetime.now(timezone.utc).isoformat(),
    )

    # Relationships
    user: Mapped[UserModel | None] = relationship()
    workspace: Mapped[WorkspaceModel | None] = relationship()


