"""
Timeout worker for handling task timeouts.

This worker periodically checks for tasks that have exceeded their timeout
and automatically fails them, freeing up assigned bots.
"""
import asyncio
import logging
from typing import Any

from ..domain.models.bot import BotStatus
from ..domain.repositories.bot_repo import BotRepository
from ..domain.repositories.task_repo import TaskRepository

logger = logging.getLogger(__name__)


class TimeoutWorker:
    """
    Background worker that processes task timeouts.

    Periodically scans for tasks that have exceeded their timeout_seconds
    and fails them automatically, freeing up any assigned bots.
    """

    def __init__(
        self,
        task_repo: TaskRepository,
        bot_repo: BotRepository,
        check_interval_seconds: int = 30,
    ) -> None:
        """
        Initialize timeout worker.

        Args:
            task_repo: Task repository for querying and updating tasks
            bot_repo: Bot repository for freeing up bots
            check_interval_seconds: How often to check for timeouts (default: 30s)
        """
        self._task_repo = task_repo
        self._bot_repo = bot_repo
        self._check_interval = check_interval_seconds
        self._running = False
        self._task: asyncio.Task[Any] | None = None

    async def process_timeouts(self) -> int:
        """
        Process all timed-out tasks.

        Finds tasks that have exceeded their timeout and fails them.
        Frees up any bots that were assigned to those tasks.

        Returns:
            Number of tasks that were timed out
        """
        # Get all tasks (we'll filter in Python for SQLite compatibility)
        all_tasks = await self._task_repo.get_all()

        timed_out_count = 0

        for task in all_tasks:
            # Check if task is timed out
            if task.is_timed_out():
                try:
                    # Fetch latest task state
                    current_task = await self._task_repo.get(task.id)
                    if not current_task:
                        continue

                    # Skip if already in terminal state
                    if current_task.is_terminal():
                        continue

                    # Fail the task
                    error_details = {
                        "reason": "timeout",
                        "message": f"Task exceeded timeout of {current_task.timeout_seconds} seconds",
                        "timeout_seconds": current_task.timeout_seconds,
                    }
                    current_task.fail(error_details)
                    await self._task_repo.save(current_task)

                    # Free up the bot if one was assigned
                    if current_task.bot_id:
                        bot = await self._bot_repo.get(current_task.bot_id)
                        if bot and bot.status == BotStatus.BUSY:
                            bot.go_online()
                            await self._bot_repo.save(bot)

                    timed_out_count += 1
                    logger.info(
                        f"Task {current_task.id} timed out after {current_task.timeout_seconds}s"
                    )

                except Exception as e:
                    logger.error(f"Error processing timeout for task {task.id}: {e}")
                    continue

        if timed_out_count > 0:
            logger.info(f"Processed {timed_out_count} timed-out tasks")

        return timed_out_count

    async def start(self) -> None:
        """
        Start the timeout worker.

        Begins periodic timeout checking in the background.
        """
        if self._running:
            logger.warning("Timeout worker already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"Timeout worker started (check interval: {self._check_interval}s)")

    async def stop(self) -> None:
        """
        Stop the timeout worker.

        Gracefully stops the background task.
        """
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info("Timeout worker stopped")

    def is_running(self) -> bool:
        """
        Check if worker is currently running.

        Returns:
            True if worker is running
        """
        return self._running

    async def _run_loop(self) -> None:
        """
        Main worker loop.

        Runs continuously, checking for timeouts at regular intervals.
        """
        while self._running:
            try:
                await self.process_timeouts()
            except Exception as e:
                logger.error(f"Error in timeout worker loop: {e}")

            # Wait for next check interval
            try:
                await asyncio.sleep(self._check_interval)
            except asyncio.CancelledError:
                break
