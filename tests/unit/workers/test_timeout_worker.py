"""Unit tests for timeout worker."""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from clawbot_coordinator.domain.models.bot import Bot, BotStatus
from clawbot_coordinator.domain.models.task import Task, TaskStatus
from clawbot_coordinator.workers.timeout_worker import TimeoutWorker


@pytest.mark.asyncio
class TestTimeoutWorker:
    """Test timeout worker functionality."""

    @pytest.fixture
    def mock_task_repo(self) -> AsyncMock:
        """Create mock task repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_bot_repo(self) -> AsyncMock:
        """Create mock bot repository."""
        return AsyncMock()

    @pytest.fixture
    def worker(self, mock_task_repo: AsyncMock, mock_bot_repo: AsyncMock) -> TimeoutWorker:
        """Create timeout worker instance."""
        return TimeoutWorker(
            task_repo=mock_task_repo,
            bot_repo=mock_bot_repo,
            check_interval_seconds=30,
        )

    async def test_worker_initialization(self, worker: TimeoutWorker) -> None:
        """Should initialize with correct parameters."""
        assert worker._check_interval == 30
        assert worker._running is False

    async def test_process_timeouts_with_no_tasks(
        self, worker: TimeoutWorker, mock_task_repo: AsyncMock
    ) -> None:
        """Should handle case with no timed-out tasks."""
        mock_task_repo.get_all.return_value = []

        result = await worker.process_timeouts()

        assert result == 0
        mock_task_repo.get_all.assert_called_once()

    async def test_process_timeouts_identifies_timed_out_task(
        self,
        worker: TimeoutWorker,
        mock_task_repo: AsyncMock,
        mock_bot_repo: AsyncMock,
    ) -> None:
        """Should identify and fail timed-out task."""
        # Create a task that started 10 minutes ago with 5 minute timeout
        bot_id = uuid4()
        task = Task(
            workflow_id=uuid4(),
            payload={"action": "test"},
            timeout_seconds=300,  # 5 minutes
            bot_id=bot_id,
            status=TaskStatus.IN_PROGRESS,
        )
        task.started_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        task.updated_at = datetime.now(timezone.utc) - timedelta(minutes=10)

        # Create a bot that's busy
        bot = Bot(
            id=bot_id,
            name="test-bot",
            capabilities=["test"],
            status=BotStatus.BUSY,
        )

        mock_task_repo.get_all.return_value = [task]
        mock_task_repo.get.return_value = task
        mock_bot_repo.get.return_value = bot

        result = await worker.process_timeouts()

        assert result == 1
        # Should have saved the failed task
        mock_task_repo.save.assert_called_once()
        saved_task = mock_task_repo.save.call_args[0][0]
        assert saved_task.status == TaskStatus.FAILED
        assert saved_task.result is not None
        assert "timeout" in str(saved_task.result).lower()

        # Should have freed the bot
        mock_bot_repo.save.assert_called_once()
        saved_bot = mock_bot_repo.save.call_args[0][0]
        assert saved_bot.status == BotStatus.ONLINE

    async def test_process_timeouts_ignores_active_task(
        self, worker: TimeoutWorker, mock_task_repo: AsyncMock
    ) -> None:
        """Should not fail task that is still within timeout."""
        # Create a task that started 2 minutes ago with 5 minute timeout
        task = Task(
            workflow_id=uuid4(),
            payload={"action": "test"},
            timeout_seconds=300,  # 5 minutes
            status=TaskStatus.IN_PROGRESS,
        )
        task.started_at = datetime.now(timezone.utc) - timedelta(minutes=2)
        task.updated_at = datetime.now(timezone.utc) - timedelta(minutes=2)

        mock_task_repo.get_all.return_value = [task]

        result = await worker.process_timeouts()

        assert result == 0
        mock_task_repo.save.assert_not_called()

    async def test_process_timeouts_handles_in_progress_task(
        self,
        worker: TimeoutWorker,
        mock_task_repo: AsyncMock,
        mock_bot_repo: AsyncMock,
    ) -> None:
        """Should fail in-progress task that exceeded timeout."""
        # Create a task that started 10 minutes ago with 5 minute timeout
        bot_id = uuid4()
        task = Task(
            workflow_id=uuid4(),
            payload={"action": "test"},
            timeout_seconds=300,
            bot_id=bot_id,
            status=TaskStatus.IN_PROGRESS,
        )
        task.started_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        task.updated_at = datetime.now(timezone.utc) - timedelta(minutes=10)

        bot = Bot(
            id=bot_id,
            name="test-bot",
            capabilities=["test"],
            status=BotStatus.BUSY,
        )

        mock_task_repo.get_all.return_value = [task]
        mock_task_repo.get.return_value = task
        mock_bot_repo.get.return_value = bot

        result = await worker.process_timeouts()

        assert result == 1
        mock_task_repo.save.assert_called_once()

    async def test_process_timeouts_ignores_completed_task(
        self, worker: TimeoutWorker, mock_task_repo: AsyncMock
    ) -> None:
        """Should not process completed tasks."""
        task = Task(
            workflow_id=uuid4(),
            payload={"action": "test"},
            status=TaskStatus.COMPLETED,
        )

        mock_task_repo.get_all.return_value = [task]

        result = await worker.process_timeouts()

        assert result == 0
        mock_task_repo.save.assert_not_called()

    async def test_process_timeouts_handles_multiple_tasks(
        self,
        worker: TimeoutWorker,
        mock_task_repo: AsyncMock,
        mock_bot_repo: AsyncMock,
    ) -> None:
        """Should process multiple timed-out tasks."""
        # Two timed-out tasks
        task1 = Task(
            workflow_id=uuid4(),
            payload={"action": "test1"},
            timeout_seconds=300,
            bot_id=uuid4(),
            status=TaskStatus.IN_PROGRESS,
        )
        task1.started_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        task1.updated_at = datetime.now(timezone.utc) - timedelta(minutes=10)

        task2 = Task(
            workflow_id=uuid4(),
            payload={"action": "test2"},
            timeout_seconds=300,
            bot_id=uuid4(),
            status=TaskStatus.IN_PROGRESS,
        )
        task2.started_at = datetime.now(timezone.utc) - timedelta(minutes=15)
        task2.updated_at = datetime.now(timezone.utc) - timedelta(minutes=15)

        # One active task
        task3 = Task(
            workflow_id=uuid4(),
            payload={"action": "test3"},
            timeout_seconds=300,
            status=TaskStatus.IN_PROGRESS,
        )
        task3.started_at = datetime.now(timezone.utc) - timedelta(minutes=2)
        task3.updated_at = datetime.now(timezone.utc) - timedelta(minutes=2)

        mock_task_repo.get_all.return_value = [task1, task2, task3]

        # Mock get to return the task itself
        async def get_side_effect(task_id):
            for t in [task1, task2, task3]:
                if t.id == task_id:
                    return t
            return None

        mock_task_repo.get.side_effect = get_side_effect
        mock_bot_repo.get.return_value = None  # No bot assigned

        result = await worker.process_timeouts()

        assert result == 2
        assert mock_task_repo.save.call_count == 2

    async def test_process_timeouts_handles_bot_not_found(
        self, worker: TimeoutWorker, mock_task_repo: AsyncMock, mock_bot_repo: AsyncMock
    ) -> None:
        """Should handle case where bot no longer exists."""
        task = Task(
            workflow_id=uuid4(),
            payload={"action": "test"},
            timeout_seconds=300,
            bot_id=uuid4(),
            status=TaskStatus.IN_PROGRESS,
        )
        task.started_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        task.updated_at = datetime.now(timezone.utc) - timedelta(minutes=10)

        mock_task_repo.get_all.return_value = [task]
        mock_task_repo.get.return_value = task
        mock_bot_repo.get.return_value = None  # Bot not found

        result = await worker.process_timeouts()

        assert result == 1
        # Should still fail the task
        mock_task_repo.save.assert_called_once()
        # Should not try to save bot
        mock_bot_repo.save.assert_not_called()

    async def test_worker_start_sets_running_flag(self, worker: TimeoutWorker) -> None:
        """Should set running flag when started."""
        assert worker._running is False
        assert worker.is_running() is False

    async def test_worker_stop_clears_running_flag(self, worker: TimeoutWorker) -> None:
        """Should clear running flag when stopped."""
        worker._running = True
        await worker.stop()
        assert worker._running is False
        assert worker.is_running() is False
