"""
Workflow domain model.

Represents an orchestrated sequence of tasks with state management.
This is a pure domain model using Pydantic - no SQLAlchemy dependencies.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from ...exceptions import InvalidStateTransition


class WorkflowStatus(str, Enum):
    """Valid states for a workflow."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Workflow(BaseModel):
    """
    Workflow domain model representing an orchestrated sequence of tasks.

    State machine transitions:
    - pending → in_progress (via start)
    - in_progress → completed (via complete)
    - in_progress → failed (via fail)
    - any → cancelled (via cancel)
    """

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., min_length=1, max_length=255, description="Workflow name")
    description: str = Field(default="", description="Workflow description")
    status: WorkflowStatus = Field(default=WorkflowStatus.PENDING)
    task_ids: list[UUID] = Field(default_factory=list, description="Ordered list of task IDs")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Arbitrary metadata")

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(
        validate_assignment=True,
    )

    def start(self) -> None:
        """
        Start workflow execution.

        Transition: pending → in_progress

        Raises:
            InvalidStateTransition: If workflow is not in pending state
        """
        if self.status != WorkflowStatus.PENDING:
            raise InvalidStateTransition(
                entity_type="Workflow",
                current_state=self.status.value,
                attempted_action="start",
            )

        self.status = WorkflowStatus.IN_PROGRESS
        self.started_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def complete(self) -> None:
        """
        Mark workflow as successfully completed.

        Transition: in_progress → completed

        Raises:
            InvalidStateTransition: If workflow is not in progress
        """
        if self.status != WorkflowStatus.IN_PROGRESS:
            raise InvalidStateTransition(
                entity_type="Workflow",
                current_state=self.status.value,
                attempted_action="complete",
            )

        self.status = WorkflowStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def fail(self) -> None:
        """
        Mark workflow as failed.

        Transition: in_progress → failed

        Raises:
            InvalidStateTransition: If workflow is not in progress
        """
        if self.status != WorkflowStatus.IN_PROGRESS:
            raise InvalidStateTransition(
                entity_type="Workflow",
                current_state=self.status.value,
                attempted_action="fail",
            )

        self.status = WorkflowStatus.FAILED
        self.completed_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def cancel(self) -> None:
        """
        Cancel workflow execution.

        Transition: any → cancelled
        Can be called from any state.
        """
        self.status = WorkflowStatus.CANCELLED
        if not self.completed_at:
            self.completed_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def add_task(self, task_id: UUID) -> None:
        """
        Add a task to the workflow.

        Tasks are executed in the order they are added.

        Args:
            task_id: UUID of the task to add
        """
        self.task_ids.append(task_id)
        self.updated_at = datetime.now(timezone.utc)

    def has_tasks(self) -> bool:
        """
        Check if workflow has any tasks.

        Returns:
            True if workflow has at least one task, False otherwise
        """
        return len(self.task_ids) > 0

    def task_count(self) -> int:
        """
        Get the number of tasks in the workflow.

        Returns:
            Number of tasks
        """
        return len(self.task_ids)

    def is_pending(self) -> bool:
        """Check if workflow is pending."""
        return self.status == WorkflowStatus.PENDING

    def is_in_progress(self) -> bool:
        """Check if workflow is currently in progress."""
        return self.status == WorkflowStatus.IN_PROGRESS

    def is_terminal(self) -> bool:
        """
        Check if workflow is in a terminal state.

        Returns:
            True if workflow is completed, failed, or cancelled
        """
        return self.status in (
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
            WorkflowStatus.CANCELLED,
        )

    def duration(self) -> float | None:
        """
        Calculate workflow execution duration in seconds.

        Returns:
            Duration in seconds if workflow has started, None otherwise
        """
        if self.started_at is None:
            return None

        if self.completed_at:
            # Workflow is finished, return total duration
            return (self.completed_at - self.started_at).total_seconds()

        # Workflow still in progress, return elapsed time
        return (datetime.now(timezone.utc) - self.started_at).total_seconds()
