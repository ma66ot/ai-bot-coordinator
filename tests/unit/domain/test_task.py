"""
Unit tests for Task domain model.

Tests state machine behavior, validation rules, and task lifecycle
without any database dependencies.
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError as PydanticValidationError

from clawbot_coordinator.domain.models.task import Task, TaskStatus
from clawbot_coordinator.exceptions import InvalidStateTransition, ValidationError


class TestTaskCreation:
    """Test Task model instantiation and defaults."""

    def test_create_task_with_minimal_fields(self) -> None:
        """Should create task with only required fields."""
        workflow_id = uuid4()
        task = Task(
            workflow_id=workflow_id,
            payload={"action": "test", "data": "hello"},
        )

        assert task.workflow_id == workflow_id
        assert task.payload == {"action": "test", "data": "hello"}
        assert task.status == TaskStatus.PENDING
        assert task.id is not None
        assert task.bot_id is None
        assert task.result is None
        assert isinstance(task.created_at, datetime)

    def test_create_task_with_all_fields(self) -> None:
        """Should create task with all fields specified."""
        task_id = uuid4()
        workflow_id = uuid4()
        bot_id = uuid4()
        now = datetime.now(timezone.utc)

        task = Task(
            id=task_id,
            workflow_id=workflow_id,
            bot_id=bot_id,
            status=TaskStatus.IN_PROGRESS,
            payload={"action": "deploy"},
            result={"status": "success"},
            timeout_seconds=600,
            created_at=now,
            started_at=now,
        )

        assert task.id == task_id
        assert task.workflow_id == workflow_id
        assert task.bot_id == bot_id
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.timeout_seconds == 600

    def test_task_requires_workflow_id(self) -> None:
        """Should reject task without workflow_id."""
        with pytest.raises((PydanticValidationError, ValidationError)):
            Task(payload={"action": "test"})  # type: ignore

    def test_task_requires_payload(self) -> None:
        """Should reject task without payload."""
        with pytest.raises((PydanticValidationError, ValidationError)):
            Task(workflow_id=uuid4())  # type: ignore


class TestTaskStateTransitions:
    """Test state machine for task status changes."""

    def test_assign_to_bot_from_pending(self) -> None:
        """Should transition pending → assigned."""
        task = Task(workflow_id=uuid4(), payload={})
        bot_id = uuid4()
        assert task.status == TaskStatus.PENDING

        task.assign_to(bot_id)

        assert task.status == TaskStatus.ASSIGNED
        assert task.bot_id == bot_id
        assert task.assigned_at is not None

    def test_assign_to_bot_from_non_pending_fails(self) -> None:
        """Should not allow assignment from non-pending state."""
        task = Task(workflow_id=uuid4(), payload={})
        task.assign_to(uuid4())  # Now assigned

        with pytest.raises(InvalidStateTransition) as exc_info:
            task.assign_to(uuid4())  # Try to reassign

        assert "assigned" in str(exc_info.value).lower()

    def test_start_task_from_assigned(self) -> None:
        """Should transition assigned → in_progress."""
        task = Task(workflow_id=uuid4(), payload={})
        task.assign_to(uuid4())

        task.start()

        assert task.status == TaskStatus.IN_PROGRESS
        assert task.started_at is not None

    def test_start_task_from_pending_fails(self) -> None:
        """Should not allow starting unassigned task."""
        task = Task(workflow_id=uuid4(), payload={})

        with pytest.raises(InvalidStateTransition) as exc_info:
            task.start()

        assert "pending" in str(exc_info.value).lower()

    def test_complete_task_from_in_progress(self) -> None:
        """Should transition in_progress → completed."""
        task = Task(workflow_id=uuid4(), payload={})
        task.assign_to(uuid4())
        task.start()

        result = {"output": "success", "metrics": {"duration": 5.2}}
        task.complete(result)

        assert task.status == TaskStatus.COMPLETED
        assert task.result == result
        assert task.completed_at is not None

    def test_complete_task_from_non_in_progress_fails(self) -> None:
        """Should not allow completing task that isn't in progress."""
        task = Task(workflow_id=uuid4(), payload={})

        with pytest.raises(InvalidStateTransition):
            task.complete({"output": "done"})

    def test_fail_task_from_in_progress(self) -> None:
        """Should transition in_progress → failed."""
        task = Task(workflow_id=uuid4(), payload={})
        task.assign_to(uuid4())
        task.start()

        error = {"error": "Connection timeout", "code": "ERR_TIMEOUT"}
        task.fail(error)

        assert task.status == TaskStatus.FAILED
        assert task.result == error
        assert task.completed_at is not None

    def test_cancel_task_from_any_state(self) -> None:
        """Should allow cancellation from any state."""
        # From pending
        task1 = Task(workflow_id=uuid4(), payload={})
        task1.cancel()
        assert task1.status == TaskStatus.CANCELLED

        # From assigned
        task2 = Task(workflow_id=uuid4(), payload={})
        task2.assign_to(uuid4())
        task2.cancel()
        assert task2.status == TaskStatus.CANCELLED

        # From in_progress
        task3 = Task(workflow_id=uuid4(), payload={})
        task3.assign_to(uuid4())
        task3.start()
        task3.cancel()
        assert task3.status == TaskStatus.CANCELLED


class TestTaskTimeout:
    """Test task timeout detection."""

    def test_is_timed_out_returns_false_when_not_started(self) -> None:
        """Should not timeout if task hasn't started."""
        task = Task(workflow_id=uuid4(), payload={}, timeout_seconds=60)

        assert task.is_timed_out() is False

    def test_is_timed_out_returns_false_when_completed(self) -> None:
        """Should not timeout if task is already completed."""
        task = Task(workflow_id=uuid4(), payload={}, timeout_seconds=60)
        task.assign_to(uuid4())
        task.start()
        task.complete({"status": "done"})

        assert task.is_timed_out() is False

    def test_is_timed_out_returns_true_after_timeout(self) -> None:
        """Should detect timeout for in-progress tasks."""
        task = Task(workflow_id=uuid4(), payload={}, timeout_seconds=60)
        task.assign_to(uuid4())
        task.start()

        # Simulate task started long ago
        task.started_at = datetime.now(timezone.utc) - timedelta(seconds=120)

        assert task.is_timed_out() is True

    def test_is_timed_out_returns_false_within_timeout(self) -> None:
        """Should not timeout if within time limit."""
        task = Task(workflow_id=uuid4(), payload={}, timeout_seconds=300)
        task.assign_to(uuid4())
        task.start()

        assert task.is_timed_out() is False


class TestTaskQueries:
    """Test task query helpers."""

    def test_is_pending_returns_correct_status(self) -> None:
        """Should correctly identify pending tasks."""
        task = Task(workflow_id=uuid4(), payload={})
        assert task.is_pending() is True

        task.assign_to(uuid4())
        assert task.is_pending() is False

    def test_is_assigned_returns_correct_status(self) -> None:
        """Should correctly identify assigned tasks."""
        task = Task(workflow_id=uuid4(), payload={})
        assert task.is_assigned() is False

        task.assign_to(uuid4())
        assert task.is_assigned() is True

        task.start()
        assert task.is_assigned() is False

    def test_is_in_progress_returns_correct_status(self) -> None:
        """Should correctly identify in-progress tasks."""
        task = Task(workflow_id=uuid4(), payload={})
        task.assign_to(uuid4())
        assert task.is_in_progress() is False

        task.start()
        assert task.is_in_progress() is True

        task.complete({})
        assert task.is_in_progress() is False

    def test_is_terminal_returns_correct_status(self) -> None:
        """Should identify terminal states (completed, failed, cancelled)."""
        # Not terminal
        task = Task(workflow_id=uuid4(), payload={})
        assert task.is_terminal() is False

        task.assign_to(uuid4())
        assert task.is_terminal() is False

        task.start()
        assert task.is_terminal() is False

        # Terminal - completed
        task.complete({})
        assert task.is_terminal() is True

        # Terminal - failed
        task2 = Task(workflow_id=uuid4(), payload={})
        task2.assign_to(uuid4())
        task2.start()
        task2.fail({"error": "test"})
        assert task2.is_terminal() is True

        # Terminal - cancelled
        task3 = Task(workflow_id=uuid4(), payload={})
        task3.cancel()
        assert task3.is_terminal() is True


class TestTaskDuration:
    """Test task duration calculation."""

    def test_duration_returns_none_when_not_started(self) -> None:
        """Should return None if task hasn't started."""
        task = Task(workflow_id=uuid4(), payload={})
        assert task.duration() is None

    def test_duration_returns_elapsed_time_when_in_progress(self) -> None:
        """Should return elapsed time for in-progress tasks."""
        task = Task(workflow_id=uuid4(), payload={})
        task.assign_to(uuid4())
        task.start()

        # Simulate task started 5 seconds ago
        task.started_at = datetime.now(timezone.utc) - timedelta(seconds=5)

        duration = task.duration()
        assert duration is not None
        assert duration >= 5.0
        assert duration < 6.0  # Allow some wiggle room

    def test_duration_returns_total_time_when_completed(self) -> None:
        """Should return total duration for completed tasks."""
        task = Task(workflow_id=uuid4(), payload={})
        task.assign_to(uuid4())
        task.start()

        # Simulate task started and completed
        task.started_at = datetime.now(timezone.utc) - timedelta(seconds=10)
        task.complete({})
        task.completed_at = task.started_at + timedelta(seconds=10)

        duration = task.duration()
        assert duration is not None
        assert 9.9 <= duration <= 10.1  # Should be approximately 10 seconds
