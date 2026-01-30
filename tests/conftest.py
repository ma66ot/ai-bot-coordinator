"""
Shared pytest fixtures for all tests.

Provides test database setup, client fixtures, and common test data.
"""
import asyncio
from typing import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from clawbot_coordinator.database import Base, BotORM, TaskORM, WorkflowORM, get_session  # noqa: F401
from clawbot_coordinator.main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the entire test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_db_engine():
    """
    Create a test database engine.

    Uses in-memory SQLite with StaticPool to share connection across async tasks.
    For PostgreSQL-specific features, use testcontainers in separate tests.
    """
    # NOTE(ai): StaticPool ensures all connections use the same in-memory database
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    await engine.dispose()


@pytest.fixture
async def test_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    session_factory = async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session
        await session.rollback()  # Rollback any uncommitted changes


@pytest.fixture
async def client(test_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Create test HTTP client with overridden dependencies.

    Uses test database session instead of production database.
    """

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield test_session

    app.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=app)  # type: ignore
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_bot_data() -> dict:
    """Sample bot data for tests."""
    return {
        "name": "test-bot",
        "capabilities": ["python", "docker"],
        "metadata": {"version": "1.0"},
    }
