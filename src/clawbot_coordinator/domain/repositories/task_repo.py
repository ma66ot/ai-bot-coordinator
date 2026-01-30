"""
Task repository interface (Port).

Abstract interface for task persistence operations.
See CLAUDE.md Protocol 3 for layer isolation rules.
"""
from abc import ABC, abstractmethod
from uuid import UUID

from ..models.task import Task


class TaskRepository(ABC):
    """Abstract repository for Task persistence operations."""

    @abstractmethod
    async def get(self, task_id: UUID) -> Task | None:
        """
        Fetch task by ID.

        Args:
            task_id: Unique identifier of the task

        Returns:
            Task if found, None otherwise
        """
        pass

    @abstractmethod
    async def save(self, task: Task) -> None:
        """
        Persist a task (insert or update).

        Must handle both new tasks and updates to existing tasks.

        Args:
            task: Task domain model to persist
        """
        pass

    @abstractmethod
    async def delete(self, task_id: UUID) -> bool:
        """
        Delete a task by ID.

        Args:
            task_id: Unique identifier of the task

        Returns:
            True if task was deleted, False if not found
        """
        pass

    @abstractmethod
    async def get_all(self, skip: int = 0, limit: int = 100) -> list[Task]:
        """
        Fetch all tasks with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Task domain models
        """
        pass

    @abstractmethod
    async def get_by_workflow(self, workflow_id: UUID) -> list[Task]:
        """
        Find all tasks belonging to a specific workflow.

        Args:
            workflow_id: Workflow identifier

        Returns:
            List of tasks in the workflow
        """
        pass

    @abstractmethod
    async def get_by_status(self, status: str) -> list[Task]:
        """
        Find all tasks with a specific status.

        Args:
            status: Task status ("pending", "assigned", "in_progress", etc.)

        Returns:
            List of tasks with the specified status
        """
        pass

    @abstractmethod
    async def get_by_bot(self, bot_id: UUID) -> list[Task]:
        """
        Find all tasks assigned to a specific bot.

        Args:
            bot_id: Bot identifier

        Returns:
            List of tasks assigned to the bot
        """
        pass

    @abstractmethod
    async def get_pending_tasks(self, limit: int = 10) -> list[Task]:
        """
        Find pending tasks ready for assignment.

        Args:
            limit: Maximum number of tasks to return

        Returns:
            List of pending tasks, ordered by creation time
        """
        pass

    @abstractmethod
    async def get_timeout_candidates(self) -> list[Task]:
        """
        Find tasks that may have timed out.

        Returns tasks that are in-progress and have exceeded their timeout.

        Returns:
            List of tasks that may need timeout handling
        """
        pass

    @abstractmethod
    async def get_active_tasks_for_bot(self, bot_id: UUID) -> list[Task]:
        """
        Find active (assigned or in-progress) tasks for a bot.

        Args:
            bot_id: Bot identifier

        Returns:
            List of active tasks for the bot
        """
        pass
