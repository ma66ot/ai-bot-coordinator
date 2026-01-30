"""API schemas for Workflow endpoints."""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from ...domain.models.workflow import Workflow, WorkflowStatus
from .task_schemas import TaskResponse


class WorkflowCreate(BaseModel):
    """Request schema for creating a workflow."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="")
    task_payloads: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowResponse(BaseModel):
    """Response schema for workflow data."""

    id: UUID
    name: str
    description: str
    status: WorkflowStatus
    task_ids: list[UUID]
    metadata: dict[str, Any]
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    updated_at: datetime

    @classmethod
    def from_domain(cls, workflow: Workflow) -> "WorkflowResponse":
        return cls(
            id=workflow.id,
            name=workflow.name,
            description=workflow.description,
            status=workflow.status,
            task_ids=workflow.task_ids,
            metadata=workflow.metadata,
            created_at=workflow.created_at,
            started_at=workflow.started_at,
            completed_at=workflow.completed_at,
            updated_at=workflow.updated_at,
        )


class WorkflowWithTasks(BaseModel):
    """Response schema for workflow with embedded tasks."""

    workflow: WorkflowResponse
    tasks: list[TaskResponse]
