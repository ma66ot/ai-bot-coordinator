"""
Database configuration and ORM setup.

This module provides:
- Async SQLAlchemy engine and session factory
- Declarative Base for ORM models
- Database initialization utilities

ORM models (BotORM, TaskORM, etc.) are defined here in infrastructure layer.
Domain models remain pure Pydantic in domain/models/.
"""
from datetime import datetime, timezone
from typing import Any, AsyncGenerator
from uuid import UUID, uuid4

from sqlalchemy import ARRAY, JSON, DateTime, ForeignKey, Index, Integer, MetaData, String, Text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .config import settings

# Naming convention for constraints (helps with Alembic migrations)
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    metadata = metadata


# ============================================================================
# ORM Models (SQLAlchemy)
# ============================================================================


class BotORM(Base):
    """
    SQLAlchemy ORM model for bots table.

    Maps to domain.models.bot.Bot via repository layer.
    """

    __tablename__ = "bots"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    capabilities: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True, default="offline")
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Regular indexes are created via mapped_column index=True
    # Note: GIN indexes on JSON require JSONB type, not JSON
    # For now, we rely on the index on 'name' and 'status' columns

    def __repr__(self) -> str:
        return f"<BotORM(id={self.id}, name={self.name}, status={self.status})>"


class TaskORM(Base):
    """
    SQLAlchemy ORM model for tasks table.

    Maps to domain.models.task.Task via repository layer.
    """

    __tablename__ = "tasks"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workflow_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    bot_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("bots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        default="pending",
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,  # For ordering pending tasks
    )
    assigned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Indexes for common queries
    __table_args__ = (
        Index("ix_tasks_workflow_status", "workflow_id", "status"),
        Index("ix_tasks_bot_status", "bot_id", "status"),
        # For timeout detection queries
        Index("ix_tasks_status_started", "status", "started_at"),
    )

    def __repr__(self) -> str:
        return f"<TaskORM(id={self.id}, workflow_id={self.workflow_id}, status={self.status})>"


class WorkflowORM(Base):
    """
    SQLAlchemy ORM model for workflows table.

    Maps to domain.models.workflow.Workflow via repository layer.
    """

    __tablename__ = "workflows"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True, default="pending")
    # Store task IDs as JSON array for SQLite compatibility
    # In production PostgreSQL, could use ARRAY(UUID)
    task_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Index for status queries
    __table_args__ = (
        Index("ix_workflows_status_created", "status", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<WorkflowORM(id={self.id}, name={self.name}, status={self.status})>"


# ============================================================================
# Database Engine and Session Management
# ============================================================================

# Global engine (initialized on first use)
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """
    Get or create the global async database engine.

    Returns:
        AsyncEngine: Configured SQLAlchemy async engine
    """
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            str(settings.database_url),
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            echo=settings.debug,
            # Connection pooling optimizations
            pool_pre_ping=True,  # Verify connections before using
            pool_recycle=3600,  # Recycle connections after 1 hour
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Get or create the global session factory.

    Returns:
        async_sessionmaker: Factory for creating async sessions
    """
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        _session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Don't expire objects after commit
            autoflush=False,  # Explicit flush control
        )
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database sessions in FastAPI routes.

    Usage:
        @router.get("/items")
        async def get_items(session: AsyncSession = Depends(get_session)):
            ...

    Yields:
        AsyncSession: Database session (auto-closed after request)
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """
    Initialize database tables.

    WARNING: Only use in development/testing.
    In production, use Alembic migrations instead.
    """
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_db() -> None:
    """
    Drop all database tables.

    WARNING: DESTRUCTIVE. Only use in testing.
    """
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def close_db() -> None:
    """
    Close database engine and cleanup connections.

    Should be called on application shutdown.
    """
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
