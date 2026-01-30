"""
Dependency injection for FastAPI routes.

Provides factory functions for services and repositories.
"""
from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_session
from .domain.services.bot_service import BotService
from .domain.services.task_service import TaskService
from .domain.services.websocket_manager import WebSocketConnectionManager
from .domain.services.workflow_service import WorkflowService
from .infrastructure.repositories.postgres_bot_repo import PostgresBotRepository
from .infrastructure.repositories.postgres_task_repo import PostgresTaskRepository
from .infrastructure.repositories.postgres_workflow_repo import PostgresWorkflowRepository

# Global singleton for WebSocket connection manager
_websocket_manager: WebSocketConnectionManager | None = None


async def get_bot_service(
    session: AsyncSession = Depends(get_session),
) -> AsyncGenerator[BotService, None]:
    """
    Dependency for getting BotService with injected repository.

    Args:
        session: Database session (injected by FastAPI)

    Yields:
        BotService instance
    """
    repo = PostgresBotRepository(session)
    yield BotService(repository=repo)


async def get_task_service(
    session: AsyncSession = Depends(get_session),
) -> AsyncGenerator[TaskService, None]:
    """
    Dependency for getting TaskService with injected repositories.

    Args:
        session: Database session (injected by FastAPI)

    Yields:
        TaskService instance
    """
    task_repo = PostgresTaskRepository(session)
    bot_repo = PostgresBotRepository(session)
    yield TaskService(task_repo=task_repo, bot_repo=bot_repo)


async def get_workflow_service(
    session: AsyncSession = Depends(get_session),
) -> AsyncGenerator[WorkflowService, None]:
    """
    Dependency for getting WorkflowService with injected repositories.

    Args:
        session: Database session (injected by FastAPI)

    Yields:
        WorkflowService instance
    """
    workflow_repo = PostgresWorkflowRepository(session)
    task_repo = PostgresTaskRepository(session)
    bot_repo = PostgresBotRepository(session)
    yield WorkflowService(
        workflow_repo=workflow_repo,
        task_repo=task_repo,
        bot_repo=bot_repo,
    )


def get_websocket_manager() -> WebSocketConnectionManager:
    """
    Dependency for getting WebSocket connection manager.

    Returns singleton instance that persists across all connections.

    Returns:
        WebSocketConnectionManager singleton
    """
    global _websocket_manager
    if _websocket_manager is None:
        _websocket_manager = WebSocketConnectionManager()
    return _websocket_manager
