"""
API schemas (DTOs) for Task endpoints.

Request and response models for task operations.
"""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from ...domain.models.task import Task, TaskStatus


class TaskCreate(BaseModel):
    """Request schema for creating a new task."""

    workflow_id: UUID = Field(..., description="Parent workflow ID")
    payload: dict[str, Any] = Field(..., description="Task input data")
    timeout_seconds: int = Field(
        default=300,
        ge=1,
        le=3600,
        description="Task timeout in seconds",
    )


class TaskAssign(BaseModel):
    """Request schema for assigning task to a bot."""

    bot_id: UUID = Field(..., description="Bot to assign task to")


class TaskResult(BaseModel):
    """Request schema for task completion or failure."""

    result: dict[str, Any] = Field(..., description="Task result or error data")


class TaskResponse(BaseModel):
    """Response schema for task data."""

    id: UUID
    workflow_id: UUID
    bot_id: UUID | None
    status: TaskStatus
    payload: dict[str, Any]
    result: dict[str, Any] | None
    timeout_seconds: int
    created_at: datetime
    assigned_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    updated_at: datetime

    @classmethod
    def from_domain(cls, task: Task) -> "TaskResponse":
        """
        Convert domain model to API response.

        Args:
            task: Task domain model

        Returns:
            TaskResponse DTO
        """
        return cls(
            id=task.id,
            workflow_id=task.workflow_id,
            bot_id=task.bot_id,
            status=task.status,
            payload=task.payload,
            result=task.result,
            timeout_seconds=task.timeout_seconds,
            created_at=task.created_at,
            assigned_at=task.assigned_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            updated_at=task.updated_at,
        )

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "workflow_id": "456e7890-e89b-12d3-a456-426614174000",
                "bot_id": "789e0123-e89b-12d3-a456-426614174000",
                "status": "in_progress",
                "payload": {"action": "deploy", "target": "production"},
                "result": None,
                "timeout_seconds": 300,
                "created_at": "2024-01-30T10:00:00Z",
                "assigned_at": "2024-01-30T10:01:00Z",
                "started_at": "2024-01-30T10:02:00Z",
                "completed_at": None,
                "updated_at": "2024-01-30T10:02:00Z",
            }
        }
    }


class TaskList(BaseModel):
    """Response schema for paginated task list."""

    items: list[TaskResponse]
    total: int
    skip: int
    limit: int

    @classmethod
    def from_domain_list(
        cls, tasks: list[Task], total: int, skip: int, limit: int
    ) -> "TaskList":
        """
        Convert list of domain models to paginated response.

        Args:
            tasks: List of Task domain models
            total: Total count of tasks
            skip: Number of items skipped
            limit: Maximum items per page

        Returns:
            TaskList DTO
        """
        return cls(
            items=[TaskResponse.from_domain(task) for task in tasks],
            total=total,
            skip=skip,
            limit=limit,
        )


class TaskStatusUpdate(BaseModel):
    """Response schema for status update operations."""

    task_id: UUID
    status: TaskStatus
    message: str
