"""
PostgreSQL implementation of TaskRepository.

Maps between Task domain models and TaskORM database models.
"""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import TaskORM
from ...domain.models.task import Task, TaskStatus
from ...domain.repositories.task_repo import TaskRepository


class PostgresTaskRepository(TaskRepository):
    """PostgreSQL implementation of the Task repository."""

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session

    async def get(self, task_id: UUID) -> Task | None:
        """Fetch task by ID."""
        result = await self._session.execute(
            select(TaskORM).where(TaskORM.id == task_id)
        )
        orm_obj = result.scalar_one_or_none()
        return self._to_domain(orm_obj) if orm_obj else None

    async def save(self, task: Task) -> None:
        """Persist a task (insert or update)."""
        result = await self._session.execute(
            select(TaskORM).where(TaskORM.id == task.id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            self._update_orm(existing, task)
        else:
            orm_obj = self._from_domain(task)
            self._session.add(orm_obj)

        await self._session.flush()

    async def delete(self, task_id: UUID) -> bool:
        """Delete a task by ID."""
        result = await self._session.execute(
            select(TaskORM).where(TaskORM.id == task_id)
        )
        orm_obj = result.scalar_one_or_none()

        if orm_obj:
            await self._session.delete(orm_obj)
            await self._session.flush()
            return True
        return False

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[Task]:
        """Fetch all tasks with pagination."""
        result = await self._session.execute(
            select(TaskORM)
            .order_by(TaskORM.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        orm_objs = result.scalars().all()
        return [self._to_domain(obj) for obj in orm_objs]

    async def get_by_workflow(self, workflow_id: UUID) -> list[Task]:
        """Find all tasks belonging to a specific workflow."""
        result = await self._session.execute(
            select(TaskORM)
            .where(TaskORM.workflow_id == workflow_id)
            .order_by(TaskORM.created_at)
        )
        orm_objs = result.scalars().all()
        return [self._to_domain(obj) for obj in orm_objs]

    async def get_by_status(self, status: str) -> list[Task]:
        """Find all tasks with a specific status."""
        result = await self._session.execute(
            select(TaskORM).where(TaskORM.status == status)
        )
        orm_objs = result.scalars().all()
        return [self._to_domain(obj) for obj in orm_objs]

    async def get_by_bot(self, bot_id: UUID) -> list[Task]:
        """Find all tasks assigned to a specific bot."""
        result = await self._session.execute(
            select(TaskORM)
            .where(TaskORM.bot_id == bot_id)
            .order_by(TaskORM.created_at.desc())
        )
        orm_objs = result.scalars().all()
        return [self._to_domain(obj) for obj in orm_objs]

    async def get_pending_tasks(self, limit: int = 10) -> list[Task]:
        """Find pending tasks ready for assignment."""
        result = await self._session.execute(
            select(TaskORM)
            .where(TaskORM.status == TaskStatus.PENDING.value)
            .order_by(TaskORM.created_at)
            .limit(limit)
        )
        orm_objs = result.scalars().all()
        return [self._to_domain(obj) for obj in orm_objs]

    async def get_timeout_candidates(self) -> list[Task]:
        """
        Find tasks that may have timed out.

        Returns tasks in-progress that were started before (now - timeout_seconds).
        """
        # NOTE(ai): Get all in-progress tasks and filter in Python for SQLite compatibility
        # In production PostgreSQL, could use:
        # WHERE status = 'in_progress' AND started_at < NOW() - (timeout_seconds * INTERVAL '1 second')
        result = await self._session.execute(
            select(TaskORM).where(TaskORM.status == TaskStatus.IN_PROGRESS.value)
        )
        orm_objs = result.scalars().all()

        # Filter for timed out tasks in Python
        now = datetime.now(timezone.utc)
        timed_out = []
        for obj in orm_objs:
            if obj.started_at:
                elapsed = (now - obj.started_at).total_seconds()
                if elapsed > obj.timeout_seconds:
                    timed_out.append(self._to_domain(obj))

        return timed_out

    async def get_active_tasks_for_bot(self, bot_id: UUID) -> list[Task]:
        """Find active (assigned or in-progress) tasks for a bot."""
        result = await self._session.execute(
            select(TaskORM).where(
                and_(
                    TaskORM.bot_id == bot_id,
                    or_(
                        TaskORM.status == TaskStatus.ASSIGNED.value,
                        TaskORM.status == TaskStatus.IN_PROGRESS.value,
                    ),
                )
            )
        )
        orm_objs = result.scalars().all()
        return [self._to_domain(obj) for obj in orm_objs]

    @staticmethod
    def _to_domain(orm_obj: TaskORM) -> Task:
        """
        Convert ORM model to domain model.

        Args:
            orm_obj: SQLAlchemy ORM object

        Returns:
            Task domain model
        """
        return Task(
            id=orm_obj.id,
            workflow_id=orm_obj.workflow_id,
            bot_id=orm_obj.bot_id,
            status=TaskStatus(orm_obj.status),
            payload=orm_obj.payload,
            result=orm_obj.result,
            timeout_seconds=orm_obj.timeout_seconds,
            created_at=orm_obj.created_at,
            assigned_at=orm_obj.assigned_at,
            started_at=orm_obj.started_at,
            completed_at=orm_obj.completed_at,
            updated_at=orm_obj.updated_at,
        )

    @staticmethod
    def _from_domain(task: Task) -> TaskORM:
        """
        Convert domain model to ORM model.

        Args:
            task: Task domain model

        Returns:
            TaskORM SQLAlchemy object
        """
        return TaskORM(
            id=task.id,
            workflow_id=task.workflow_id,
            bot_id=task.bot_id,
            status=task.status.value,
            payload=task.payload,
            result=task.result,
            timeout_seconds=task.timeout_seconds,
            created_at=task.created_at,
            assigned_at=task.assigned_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            updated_at=task.updated_at,
        )

    @staticmethod
    def _update_orm(orm_obj: TaskORM, task: Task) -> None:
        """
        Update ORM object fields from domain model.

        Args:
            orm_obj: Existing SQLAlchemy ORM object to update
            task: Source Task domain model
        """
        orm_obj.workflow_id = task.workflow_id
        orm_obj.bot_id = task.bot_id
        orm_obj.status = task.status.value
        orm_obj.payload = task.payload
        orm_obj.result = task.result
        orm_obj.timeout_seconds = task.timeout_seconds
        orm_obj.assigned_at = task.assigned_at
        orm_obj.started_at = task.started_at
        orm_obj.completed_at = task.completed_at
        orm_obj.updated_at = task.updated_at
