"""
Unit tests for TaskService.

Tests business logic with mocked repositories - no database required.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from clawbot_coordinator.domain.models.bot import Bot, BotStatus
from clawbot_coordinator.domain.models.task import Task, TaskStatus
from clawbot_coordinator.domain.repositories.bot_repo import BotRepository
from clawbot_coordinator.domain.repositories.task_repo import TaskRepository
from clawbot_coordinator.domain.services.task_service import TaskService
from clawbot_coordinator.exceptions import ResourceNotFound


@pytest.fixture
def mock_task_repo() -> AsyncMock:
    """Create a mocked TaskRepository."""
    return AsyncMock(spec=TaskRepository)


@pytest.fixture
def mock_bot_repo() -> AsyncMock:
    """Create a mocked BotRepository."""
    return AsyncMock(spec=BotRepository)


@pytest.fixture
def service(mock_task_repo: AsyncMock, mock_bot_repo: AsyncMock) -> TaskService:
    """Create TaskService with mocked repositories."""
    return TaskService(task_repo=mock_task_repo, bot_repo=mock_bot_repo)


class TestCreateTask:
    """Test task creation."""

    async def test_create_task_returns_new_task(
        self, service: TaskService, mock_task_repo: AsyncMock
    ) -> None:
        """Should create and save a new task."""
        workflow_id = uuid4()
        payload = {"action": "deploy", "target": "production"}
        mock_task_repo.save = AsyncMock()

        task = await service.create_task(workflow_id=workflow_id, payload=payload)

        assert task.workflow_id == workflow_id
        assert task.payload == payload
        assert task.status == TaskStatus.PENDING
        mock_task_repo.save.assert_called_once()

    async def test_create_task_with_custom_timeout(
        self, service: TaskService, mock_task_repo: AsyncMock
    ) -> None:
        """Should accept custom timeout."""
        mock_task_repo.save = AsyncMock()

        task = await service.create_task(
            workflow_id=uuid4(),
            payload={},
            timeout_seconds=600,
        )

        assert task.timeout_seconds == 600


class TestAssignTask:
    """Test task assignment to bots."""

    async def test_assign_task_to_bot(
        self,
        service: TaskService,
        mock_task_repo: AsyncMock,
        mock_bot_repo: AsyncMock,
    ) -> None:
        """Should assign pending task to bot."""
        task_id = uuid4()
        bot_id = uuid4()
        task = Task(id=task_id, workflow_id=uuid4(), payload={})
        bot = Bot(id=bot_id, name="worker", capabilities=["python"])
        bot.go_online()

        mock_task_repo.get = AsyncMock(return_value=task)
        mock_bot_repo.get = AsyncMock(return_value=bot)
        mock_task_repo.save = AsyncMock()

        await service.assign_task_to_bot(task_id, bot_id)

        mock_task_repo.save.assert_called_once()
        saved_task = mock_task_repo.save.call_args[0][0]
        assert saved_task.status == TaskStatus.ASSIGNED
        assert saved_task.bot_id == bot_id

    async def test_assign_task_raises_if_task_not_found(
        self, service: TaskService, mock_task_repo: AsyncMock
    ) -> None:
        """Should raise ResourceNotFound if task doesn't exist."""
        mock_task_repo.get = AsyncMock(return_value=None)

        with pytest.raises(ResourceNotFound) as exc_info:
            await service.assign_task_to_bot(uuid4(), uuid4())

        assert "Task" in str(exc_info.value)

    async def test_assign_task_raises_if_bot_not_found(
        self,
        service: TaskService,
        mock_task_repo: AsyncMock,
        mock_bot_repo: AsyncMock,
    ) -> None:
        """Should raise ResourceNotFound if bot doesn't exist."""
        task = Task(workflow_id=uuid4(), payload={})
        mock_task_repo.get = AsyncMock(return_value=task)
        mock_bot_repo.get = AsyncMock(return_value=None)

        with pytest.raises(ResourceNotFound) as exc_info:
            await service.assign_task_to_bot(task.id, uuid4())

        assert "Bot" in str(exc_info.value)


class TestStartTask:
    """Test starting task execution."""

    async def test_start_task(
        self, service: TaskService, mock_task_repo: AsyncMock
    ) -> None:
        """Should start an assigned task."""
        task = Task(workflow_id=uuid4(), payload={})
        task.assign_to(uuid4())

        mock_task_repo.get = AsyncMock(return_value=task)
        mock_task_repo.save = AsyncMock()

        await service.start_task(task.id)

        saved_task = mock_task_repo.save.call_args[0][0]
        assert saved_task.status == TaskStatus.IN_PROGRESS
        assert saved_task.started_at is not None


class TestCompleteTask:
    """Test task completion."""

    async def test_complete_task_with_success(
        self, service: TaskService, mock_task_repo: AsyncMock, mock_bot_repo: AsyncMock
    ) -> None:
        """Should complete task and mark bot available."""
        bot_id = uuid4()
        task = Task(workflow_id=uuid4(), payload={})
        task.assign_to(bot_id)
        task.start()

        bot = Bot(id=bot_id, name="worker", capabilities=["test"])
        bot.go_online()
        bot.go_busy()

        mock_task_repo.get = AsyncMock(return_value=task)
        mock_bot_repo.get = AsyncMock(return_value=bot)
        mock_task_repo.save = AsyncMock()
        mock_bot_repo.save = AsyncMock()

        result = {"output": "success", "duration": 5.2}
        await service.complete_task(task.id, result)

        # Verify task completed
        saved_task = mock_task_repo.save.call_args[0][0]
        assert saved_task.status == TaskStatus.COMPLETED
        assert saved_task.result == result

        # Verify bot marked available
        mock_bot_repo.save.assert_called_once()
        saved_bot = mock_bot_repo.save.call_args[0][0]
        assert saved_bot.status == BotStatus.ONLINE


class TestFailTask:
    """Test task failure handling."""

    async def test_fail_task(
        self, service: TaskService, mock_task_repo: AsyncMock, mock_bot_repo: AsyncMock
    ) -> None:
        """Should fail task and mark bot available."""
        bot_id = uuid4()
        task = Task(workflow_id=uuid4(), payload={})
        task.assign_to(bot_id)
        task.start()

        bot = Bot(id=bot_id, name="worker", capabilities=["test"])
        bot.go_online()
        bot.go_busy()

        mock_task_repo.get = AsyncMock(return_value=task)
        mock_bot_repo.get = AsyncMock(return_value=bot)
        mock_task_repo.save = AsyncMock()
        mock_bot_repo.save = AsyncMock()

        error = {"error": "Connection timeout", "code": "ERR_TIMEOUT"}
        await service.fail_task(task.id, error)

        saved_task = mock_task_repo.save.call_args[0][0]
        assert saved_task.status == TaskStatus.FAILED
        assert saved_task.result == error


class TestGetTask:
    """Test getting task by ID."""

    async def test_get_task_returns_existing_task(
        self, service: TaskService, mock_task_repo: AsyncMock
    ) -> None:
        """Should return task if found."""
        task = Task(workflow_id=uuid4(), payload={})
        mock_task_repo.get = AsyncMock(return_value=task)

        result = await service.get_task(task.id)

        assert result == task

    async def test_get_task_raises_if_not_found(
        self, service: TaskService, mock_task_repo: AsyncMock
    ) -> None:
        """Should raise ResourceNotFound if task doesn't exist."""
        mock_task_repo.get = AsyncMock(return_value=None)

        with pytest.raises(ResourceNotFound):
            await service.get_task(uuid4())


class TestGetPendingTasks:
    """Test getting pending tasks."""

    async def test_get_pending_tasks(
        self, service: TaskService, mock_task_repo: AsyncMock
    ) -> None:
        """Should return pending tasks."""
        tasks = [
            Task(workflow_id=uuid4(), payload={}),
            Task(workflow_id=uuid4(), payload={}),
        ]
        mock_task_repo.get_pending_tasks = AsyncMock(return_value=tasks)

        result = await service.get_pending_tasks(limit=10)

        assert len(result) == 2
        mock_task_repo.get_pending_tasks.assert_called_once_with(10)


class TestHandleTimedOutTasks:
    """Test timeout handling."""

    async def test_handle_timed_out_tasks(
        self, service: TaskService, mock_task_repo: AsyncMock, mock_bot_repo: AsyncMock
    ) -> None:
        """Should fail timed out tasks and free bots."""
        bot_id = uuid4()
        task = Task(workflow_id=uuid4(), payload={}, timeout_seconds=60)
        task.assign_to(bot_id)
        task.start()
        task.started_at = datetime.now(timezone.utc) - timedelta(seconds=120)

        bot = Bot(id=bot_id, name="worker", capabilities=["test"])
        bot.go_online()
        bot.go_busy()

        mock_task_repo.get_timeout_candidates = AsyncMock(return_value=[task])
        mock_bot_repo.get = AsyncMock(return_value=bot)
        mock_task_repo.save = AsyncMock()
        mock_bot_repo.save = AsyncMock()

        failed_count = await service.handle_timed_out_tasks()

        assert failed_count == 1
        # Verify task failed
        saved_task = mock_task_repo.save.call_args[0][0]
        assert saved_task.status == TaskStatus.FAILED
        assert "timeout" in str(saved_task.result).lower()

        # Verify bot freed
        assert mock_bot_repo.save.called


class TestCancelTask:
    """Test task cancellation."""

    async def test_cancel_task(
        self, service: TaskService, mock_task_repo: AsyncMock
    ) -> None:
        """Should cancel task."""
        task = Task(workflow_id=uuid4(), payload={})
        mock_task_repo.get = AsyncMock(return_value=task)
        mock_task_repo.save = AsyncMock()

        await service.cancel_task(task.id)

        saved_task = mock_task_repo.save.call_args[0][0]
        assert saved_task.status == TaskStatus.CANCELLED


class TestGetTasksByWorkflow:
    """Test getting tasks by workflow."""

    async def test_get_tasks_by_workflow(
        self, service: TaskService, mock_task_repo: AsyncMock
    ) -> None:
        """Should return all tasks for workflow."""
        workflow_id = uuid4()
        tasks = [
            Task(workflow_id=workflow_id, payload={}),
            Task(workflow_id=workflow_id, payload={}),
        ]
        mock_task_repo.get_by_workflow = AsyncMock(return_value=tasks)

        result = await service.get_tasks_by_workflow(workflow_id)

        assert len(result) == 2
        mock_task_repo.get_by_workflow.assert_called_once_with(workflow_id)
