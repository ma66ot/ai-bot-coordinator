"""
FastAPI application entry point.

Creates and configures the FastAPI application with all routes and middleware.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .api.routes import bots, tasks, websocket, workflows
from .config import settings
from .database import close_db, get_session_factory, init_db
from .infrastructure.repositories.postgres_bot_repo import PostgresBotRepository
from .infrastructure.repositories.postgres_task_repo import PostgresTaskRepository
from .workers.timeout_worker import TimeoutWorker


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.

    Handles startup and shutdown events including timeout worker.
    """
    # Startup
    if settings.environment == "development":
        # Only auto-create tables in development
        await init_db()

    # Start timeout worker
    timeout_worker = None
    session = None
    try:
        # Create a dedicated session for the timeout worker
        # This session lives for the entire application lifetime
        session_factory = get_session_factory()
        session = session_factory()

        # Create repositories for timeout worker
        task_repo = PostgresTaskRepository(session)
        bot_repo = PostgresBotRepository(session)
        timeout_worker = TimeoutWorker(
            task_repo=task_repo,
            bot_repo=bot_repo,
            check_interval_seconds=30,
        )
        await timeout_worker.start()

        yield

    finally:
        # Shutdown
        if timeout_worker and timeout_worker.is_running():
            await timeout_worker.stop()
        if session:
            await session.close()
        await close_db()


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Task orchestration system for bot management",
    lifespan=lifespan,
    debug=settings.debug,
)


# Include routers
app.include_router(bots.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(workflows.router, prefix="/api/v1")
app.include_router(websocket.router, prefix="/api/v1")


# Root endpoint
@app.get("/", tags=["health"])
async def root() -> dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "environment": settings.environment,
    }


@app.get("/health", tags=["health"])
async def health_check() -> JSONResponse:
    """Detailed health check."""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": settings.app_name,
            "version": "0.1.0",
        },
    )
