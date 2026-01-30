"""
Task domain model.

Represents a unit of work to be executed by a bot with strict state machine behavior.
This is a pure domain model using Pydantic - no SQLAlchemy dependencies.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from ...exceptions import InvalidStateTransition


class TaskStatus(str, Enum):
    """Valid states for a task."""

    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task(BaseModel):
    """
    Task domain model representing a unit of work.

    State machine transitions (see CLAUDE.md Gate 4):
    - pending → assigned (via assign_to)
    - assigned → in_progress (via start)
    - in_progress → completed (via complete)
    - in_progress → failed (via fail)
    - any → cancelled (via cancel)
    """

    id: UUID = Field(default_factory=uuid4)
    workflow_id: UUID = Field(..., description="Parent workflow this task belongs to")
    bot_id: UUID | None = Field(default=None, description="Bot assigned to this task")
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    payload: dict[str, Any] = Field(..., description="Task input data")
    result: dict[str, Any] | None = Field(default=None, description="Task output data or error")
    timeout_seconds: int = Field(default=300, ge=1, le=3600, description="Task timeout in seconds")

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    assigned_at: datetime | None = Field(default=None)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(
        validate_assignment=True,
    )

    def assign_to(self, bot_id: UUID) -> None:
        """
        Assign task to a bot.

        Transition: pending → assigned

        Args:
            bot_id: UUID of the bot to assign

        Raises:
            InvalidStateTransition: If task is not in pending state
        """
        if self.status != TaskStatus.PENDING:
            raise InvalidStateTransition(
                entity_type="Task",
                current_state=self.status.value,
                attempted_action="assign_to",
            )

        self.status = TaskStatus.ASSIGNED
        self.bot_id = bot_id
        self.assigned_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def start(self) -> None:
        """
        Start task execution.

        Transition: assigned → in_progress

        Raises:
            InvalidStateTransition: If task is not in assigned state
        """
        if self.status != TaskStatus.ASSIGNED:
            raise InvalidStateTransition(
                entity_type="Task",
                current_state=self.status.value,
                attempted_action="start",
            )

        self.status = TaskStatus.IN_PROGRESS
        self.started_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def complete(self, result: dict[str, Any]) -> None:
        """
        Mark task as successfully completed.

        Transition: in_progress → completed

        Args:
            result: Task execution result data

        Raises:
            InvalidStateTransition: If task is not in progress
        """
        if self.status != TaskStatus.IN_PROGRESS:
            raise InvalidStateTransition(
                entity_type="Task",
                current_state=self.status.value,
                attempted_action="complete",
            )

        self.status = TaskStatus.COMPLETED
        self.result = result
        self.completed_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def fail(self, error: dict[str, Any]) -> None:
        """
        Mark task as failed.

        Transition: in_progress → failed

        Args:
            error: Error information

        Raises:
            InvalidStateTransition: If task is not in progress
        """
        if self.status != TaskStatus.IN_PROGRESS:
            raise InvalidStateTransition(
                entity_type="Task",
                current_state=self.status.value,
                attempted_action="fail",
            )

        self.status = TaskStatus.FAILED
        self.result = error
        self.completed_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def cancel(self) -> None:
        """
        Cancel task execution.

        Transition: any → cancelled
        Can be called from any state.
        """
        self.status = TaskStatus.CANCELLED
        self.completed_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def is_timed_out(self) -> bool:
        """
        Check if task has exceeded its timeout.

        Returns:
            True if task is in-progress and has exceeded timeout, False otherwise
        """
        if self.status != TaskStatus.IN_PROGRESS:
            return False

        if self.started_at is None:
            return False

        elapsed = (datetime.now(timezone.utc) - self.started_at).total_seconds()
        return elapsed > self.timeout_seconds

    def is_pending(self) -> bool:
        """Check if task is pending."""
        return self.status == TaskStatus.PENDING

    def is_assigned(self) -> bool:
        """Check if task is assigned to a bot."""
        return self.status == TaskStatus.ASSIGNED

    def is_in_progress(self) -> bool:
        """Check if task is currently in progress."""
        return self.status == TaskStatus.IN_PROGRESS

    def is_terminal(self) -> bool:
        """
        Check if task is in a terminal state.

        Returns:
            True if task is completed, failed, or cancelled
        """
        return self.status in (
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        )

    def duration(self) -> float | None:
        """
        Calculate task execution duration in seconds.

        Returns:
            Duration in seconds if task has started, None otherwise
        """
        if self.started_at is None:
            return None

        if self.completed_at:
            # Task is finished, return total duration
            return (self.completed_at - self.started_at).total_seconds()

        # Task still in progress, return elapsed time
        return (datetime.now(timezone.utc) - self.started_at).total_seconds()
