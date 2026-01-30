"""
Unit tests for Workflow domain model.

Tests workflow orchestration, state management, and task coordination.
"""
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError as PydanticValidationError

from clawbot_coordinator.domain.models.workflow import Workflow, WorkflowStatus
from clawbot_coordinator.exceptions import InvalidStateTransition


class TestWorkflowCreation:
    """Test Workflow model instantiation and defaults."""

    def test_create_workflow_with_minimal_fields(self) -> None:
        """Should create workflow with only required fields."""
        workflow = Workflow(name="Deployment Pipeline")

        assert workflow.name == "Deployment Pipeline"
        assert workflow.status == WorkflowStatus.PENDING
        assert workflow.id is not None
        assert workflow.description == ""
        assert workflow.task_ids == []
        assert isinstance(workflow.created_at, datetime)

    def test_create_workflow_with_all_fields(self) -> None:
        """Should create workflow with all fields specified."""
        workflow_id = uuid4()
        task_ids = [uuid4(), uuid4(), uuid4()]
        now = datetime.now(timezone.utc)

        workflow = Workflow(
            id=workflow_id,
            name="E2E Test Suite",
            description="Full integration test workflow",
            status=WorkflowStatus.IN_PROGRESS,
            task_ids=task_ids,
            created_at=now,
            started_at=now,
        )

        assert workflow.id == workflow_id
        assert workflow.name == "E2E Test Suite"
        assert workflow.description == "Full integration test workflow"
        assert workflow.status == WorkflowStatus.IN_PROGRESS
        assert workflow.task_ids == task_ids

    def test_workflow_requires_name(self) -> None:
        """Should reject workflow without name."""
        with pytest.raises(PydanticValidationError):
            Workflow()  # type: ignore


class TestWorkflowStateTransitions:
    """Test state machine for workflow status changes."""

    def test_start_workflow_from_pending(self) -> None:
        """Should transition pending → in_progress."""
        workflow = Workflow(name="Test")
        assert workflow.status == WorkflowStatus.PENDING

        workflow.start()

        assert workflow.status == WorkflowStatus.IN_PROGRESS
        assert workflow.started_at is not None

    def test_start_workflow_from_non_pending_fails(self) -> None:
        """Should not allow starting already started workflow."""
        workflow = Workflow(name="Test")
        workflow.start()

        with pytest.raises(InvalidStateTransition):
            workflow.start()

    def test_complete_workflow_from_in_progress(self) -> None:
        """Should transition in_progress → completed."""
        workflow = Workflow(name="Test")
        workflow.start()

        workflow.complete()

        assert workflow.status == WorkflowStatus.COMPLETED
        assert workflow.completed_at is not None

    def test_complete_workflow_from_pending_fails(self) -> None:
        """Should not allow completing unstarted workflow."""
        workflow = Workflow(name="Test")

        with pytest.raises(InvalidStateTransition):
            workflow.complete()

    def test_fail_workflow_from_in_progress(self) -> None:
        """Should transition in_progress → failed."""
        workflow = Workflow(name="Test")
        workflow.start()

        workflow.fail()

        assert workflow.status == WorkflowStatus.FAILED
        assert workflow.completed_at is not None

    def test_cancel_workflow_from_any_state(self) -> None:
        """Should allow cancellation from any state."""
        # From pending
        workflow1 = Workflow(name="Test1")
        workflow1.cancel()
        assert workflow1.status == WorkflowStatus.CANCELLED

        # From in_progress
        workflow2 = Workflow(name="Test2")
        workflow2.start()
        workflow2.cancel()
        assert workflow2.status == WorkflowStatus.CANCELLED


class TestWorkflowTaskManagement:
    """Test task management within workflow."""

    def test_add_task_to_workflow(self) -> None:
        """Should add task ID to workflow."""
        workflow = Workflow(name="Test")
        task_id = uuid4()

        workflow.add_task(task_id)

        assert task_id in workflow.task_ids
        assert len(workflow.task_ids) == 1

    def test_add_multiple_tasks(self) -> None:
        """Should maintain task order."""
        workflow = Workflow(name="Test")
        task_ids = [uuid4(), uuid4(), uuid4()]

        for task_id in task_ids:
            workflow.add_task(task_id)

        assert workflow.task_ids == task_ids

    def test_has_tasks_returns_true_when_tasks_exist(self) -> None:
        """Should detect when workflow has tasks."""
        workflow = Workflow(name="Test")
        assert workflow.has_tasks() is False

        workflow.add_task(uuid4())
        assert workflow.has_tasks() is True

    def test_task_count_returns_correct_number(self) -> None:
        """Should return number of tasks."""
        workflow = Workflow(name="Test")
        assert workflow.task_count() == 0

        workflow.add_task(uuid4())
        workflow.add_task(uuid4())
        assert workflow.task_count() == 2


class TestWorkflowStatusChecks:
    """Test workflow status query methods."""

    def test_is_pending_returns_correct_status(self) -> None:
        """Should correctly identify pending workflows."""
        workflow = Workflow(name="Test")
        assert workflow.is_pending() is True

        workflow.start()
        assert workflow.is_pending() is False

    def test_is_in_progress_returns_correct_status(self) -> None:
        """Should correctly identify in-progress workflows."""
        workflow = Workflow(name="Test")
        assert workflow.is_in_progress() is False

        workflow.start()
        assert workflow.is_in_progress() is True

        workflow.complete()
        assert workflow.is_in_progress() is False

    def test_is_terminal_returns_correct_status(self) -> None:
        """Should identify terminal states."""
        # Not terminal
        workflow = Workflow(name="Test")
        assert workflow.is_terminal() is False

        workflow.start()
        assert workflow.is_terminal() is False

        # Terminal - completed
        workflow.complete()
        assert workflow.is_terminal() is True

        # Terminal - failed
        workflow2 = Workflow(name="Test2")
        workflow2.start()
        workflow2.fail()
        assert workflow2.is_terminal() is True

        # Terminal - cancelled
        workflow3 = Workflow(name="Test3")
        workflow3.cancel()
        assert workflow3.is_terminal() is True


class TestWorkflowDuration:
    """Test workflow duration calculation."""

    def test_duration_returns_none_when_not_started(self) -> None:
        """Should return None if workflow hasn't started."""
        workflow = Workflow(name="Test")
        assert workflow.duration() is None

    def test_duration_returns_elapsed_time_when_in_progress(self) -> None:
        """Should return elapsed time for in-progress workflows."""
        workflow = Workflow(name="Test")
        workflow.start()

        duration = workflow.duration()
        assert duration is not None
        assert duration >= 0

    def test_duration_returns_total_time_when_completed(self) -> None:
        """Should return total duration for completed workflows."""
        from datetime import timedelta

        workflow = Workflow(name="Test")
        workflow.start()
        workflow.started_at = datetime.now(timezone.utc) - timedelta(seconds=10)
        workflow.complete()
        workflow.completed_at = workflow.started_at + timedelta(seconds=10)

        duration = workflow.duration()
        assert duration is not None
        assert 9.9 <= duration <= 10.1  # Approximately 10 seconds


class TestWorkflowMetadata:
    """Test workflow metadata handling."""

    def test_workflow_stores_metadata(self) -> None:
        """Should store arbitrary metadata."""
        workflow = Workflow(
            name="Test",
            metadata={"project": "clawbot", "environment": "staging"},
        )

        assert workflow.metadata["project"] == "clawbot"
        assert workflow.metadata["environment"] == "staging"

    def test_workflow_metadata_defaults_to_empty_dict(self) -> None:
        """Should default to empty dict if not provided."""
        workflow = Workflow(name="Test")
        assert workflow.metadata == {}
