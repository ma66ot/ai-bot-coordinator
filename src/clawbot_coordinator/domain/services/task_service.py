"""
Task service - business logic for task management.

Coordinates task lifecycle, assignment to bots, and workflow integration.
Accepts repository interfaces for dependency injection (see CLAUDE.md Checkpoint 3).
"""
from typing import Any
from uuid import UUID

from ..models.bot import BotStatus
from ..models.task import Task
from ..repositories.bot_repo import BotRepository
from ..repositories.task_repo import TaskRepository
from ...exceptions import ResourceNotFound


class TaskService:
    """
    Service layer for task management.

    Orchestrates business logic for task operations and bot coordination.
    """

    def __init__(self, task_repo: TaskRepository, bot_repo: BotRepository) -> None:
        """
        Initialize service with repository dependencies.

        Args:
            task_repo: TaskRepository interface
            bot_repo: BotRepository interface
        """
        self._task_repo = task_repo
        self._bot_repo = bot_repo

    async def create_task(
        self,
        workflow_id: UUID,
        payload: dict[str, Any],
        timeout_seconds: int = 300,
    ) -> Task:
        """
        Create a new task.

        Creates task in pending state, ready for assignment.

        Args:
            workflow_id: Parent workflow ID
            payload: Task input data
            timeout_seconds: Task timeout in seconds

        Returns:
            Newly created Task instance
        """
        task = Task(
            workflow_id=workflow_id,
            payload=payload,
            timeout_seconds=timeout_seconds,
        )

        await self._task_repo.save(task)
        return task

    async def assign_task_to_bot(self, task_id: UUID, bot_id: UUID) -> None:
        """
        Assign task to a bot.

        Args:
            task_id: ID of task to assign
            bot_id: ID of bot to assign to

        Raises:
            ResourceNotFound: If task or bot doesn't exist
            InvalidStateTransition: If task is not pending
        """
        task = await self._task_repo.get(task_id)
        if not task:
            raise ResourceNotFound("Task", str(task_id))

        bot = await self._bot_repo.get(bot_id)
        if not bot:
            raise ResourceNotFound("Bot", str(bot_id))

        task.assign_to(bot_id)
        await self._task_repo.save(task)

    async def start_task(self, task_id: UUID) -> None:
        """
        Start task execution.

        Args:
            task_id: ID of task to start

        Raises:
            ResourceNotFound: If task doesn't exist
            InvalidStateTransition: If task is not assigned
        """
        task = await self._task_repo.get(task_id)
        if not task:
            raise ResourceNotFound("Task", str(task_id))

        task.start()
        await self._task_repo.save(task)

    async def complete_task(self, task_id: UUID, result: dict[str, Any]) -> None:
        """
        Mark task as completed.

        Also marks the assigned bot as available again.

        Args:
            task_id: ID of task to complete
            result: Task execution result

        Raises:
            ResourceNotFound: If task doesn't exist
            InvalidStateTransition: If task is not in progress
        """
        task = await self._task_repo.get(task_id)
        if not task:
            raise ResourceNotFound("Task", str(task_id))

        task.complete(result)
        await self._task_repo.save(task)

        # Free the bot if task was assigned
        if task.bot_id:
            bot = await self._bot_repo.get(task.bot_id)
            if bot and bot.status == BotStatus.BUSY:
                bot.go_online()  # Mark bot available again
                await self._bot_repo.save(bot)

    async def fail_task(self, task_id: UUID, error: dict[str, Any]) -> None:
        """
        Mark task as failed.

        Also marks the assigned bot as available again.

        Args:
            task_id: ID of task to fail
            error: Error information

        Raises:
            ResourceNotFound: If task doesn't exist
            InvalidStateTransition: If task is not in progress
        """
        task = await self._task_repo.get(task_id)
        if not task:
            raise ResourceNotFound("Task", str(task_id))

        task.fail(error)
        await self._task_repo.save(task)

        # Free the bot if task was assigned
        if task.bot_id:
            bot = await self._bot_repo.get(task.bot_id)
            if bot and bot.status == BotStatus.BUSY:
                bot.go_online()
                await self._bot_repo.save(bot)

    async def cancel_task(self, task_id: UUID) -> None:
        """
        Cancel a task.

        Can be called from any state.

        Args:
            task_id: ID of task to cancel

        Raises:
            ResourceNotFound: If task doesn't exist
        """
        task = await self._task_repo.get(task_id)
        if not task:
            raise ResourceNotFound("Task", str(task_id))

        task.cancel()
        await self._task_repo.save(task)

        # Free the bot if task was assigned and bot is busy
        if task.bot_id:
            bot = await self._bot_repo.get(task.bot_id)
            if bot and bot.status == BotStatus.BUSY:
                bot.go_online()
                await self._bot_repo.save(bot)

    async def get_task(self, task_id: UUID) -> Task:
        """
        Fetch task by ID.

        Args:
            task_id: ID of task to fetch

        Returns:
            Task instance

        Raises:
            ResourceNotFound: If task doesn't exist
        """
        task = await self._task_repo.get(task_id)
        if not task:
            raise ResourceNotFound("Task", str(task_id))
        return task

    async def get_pending_tasks(self, limit: int = 10) -> list[Task]:
        """
        Get pending tasks ready for assignment.

        Args:
            limit: Maximum number of tasks to return

        Returns:
            List of pending tasks
        """
        return await self._task_repo.get_pending_tasks(limit)

    async def get_tasks_by_workflow(self, workflow_id: UUID) -> list[Task]:
        """
        Get all tasks for a workflow.

        Args:
            workflow_id: Workflow ID

        Returns:
            List of tasks in the workflow
        """
        return await self._task_repo.get_by_workflow(workflow_id)

    async def get_tasks_by_bot(self, bot_id: UUID) -> list[Task]:
        """
        Get all tasks assigned to a bot.

        Args:
            bot_id: Bot ID

        Returns:
            List of tasks assigned to the bot
        """
        return await self._task_repo.get_by_bot(bot_id)

    async def handle_timed_out_tasks(self) -> int:
        """
        Handle tasks that have exceeded their timeout.

        Fails timed-out tasks and frees their bots.

        Returns:
            Number of tasks that were failed due to timeout
        """
        timeout_tasks = await self._task_repo.get_timeout_candidates()
        failed_count = 0

        for task in timeout_tasks:
            if task.is_timed_out():
                # Fail the task
                task.fail({"error": "Task exceeded timeout", "timeout_seconds": task.timeout_seconds})
                await self._task_repo.save(task)
                failed_count += 1

                # Free the bot
                if task.bot_id:
                    bot = await self._bot_repo.get(task.bot_id)
                    if bot and bot.status == BotStatus.BUSY:
                        bot.go_online()
                        await self._bot_repo.save(bot)

        return failed_count

    async def list_tasks(self, skip: int = 0, limit: int = 100) -> list[Task]:
        """
        List all tasks with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of tasks
        """
        return await self._task_repo.get_all(skip=skip, limit=limit)

    async def delete_task(self, task_id: UUID) -> None:
        """
        Delete a task from the system.

        Args:
            task_id: ID of task to delete

        Raises:
            ResourceNotFound: If task doesn't exist
        """
        deleted = await self._task_repo.delete(task_id)
        if not deleted:
            raise ResourceNotFound("Task", str(task_id))
