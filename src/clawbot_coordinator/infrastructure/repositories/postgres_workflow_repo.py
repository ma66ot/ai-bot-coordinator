"""
PostgreSQL implementation of WorkflowRepository.

Maps between Workflow domain models and WorkflowORM database models.
"""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import WorkflowORM
from ...domain.models.workflow import Workflow, WorkflowStatus
from ...domain.repositories.workflow_repo import WorkflowRepository


class PostgresWorkflowRepository(WorkflowRepository):
    """PostgreSQL implementation of the Workflow repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, workflow_id: UUID) -> Workflow | None:
        result = await self._session.execute(
            select(WorkflowORM).where(WorkflowORM.id == workflow_id)
        )
        orm_obj = result.scalar_one_or_none()
        return self._to_domain(orm_obj) if orm_obj else None

    async def save(self, workflow: Workflow) -> None:
        result = await self._session.execute(
            select(WorkflowORM).where(WorkflowORM.id == workflow.id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            self._update_orm(existing, workflow)
        else:
            orm_obj = self._from_domain(workflow)
            self._session.add(orm_obj)

        await self._session.flush()

    async def delete(self, workflow_id: UUID) -> bool:
        result = await self._session.execute(
            select(WorkflowORM).where(WorkflowORM.id == workflow_id)
        )
        orm_obj = result.scalar_one_or_none()

        if orm_obj:
            await self._session.delete(orm_obj)
            await self._session.flush()
            return True
        return False

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[Workflow]:
        result = await self._session.execute(
            select(WorkflowORM)
            .order_by(WorkflowORM.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        orm_objs = result.scalars().all()
        return [self._to_domain(obj) for obj in orm_objs]

    async def get_by_status(self, status: str) -> list[Workflow]:
        result = await self._session.execute(
            select(WorkflowORM).where(WorkflowORM.status == status)
        )
        orm_objs = result.scalars().all()
        return [self._to_domain(obj) for obj in orm_objs]

    async def get_active_workflows(self) -> list[Workflow]:
        result = await self._session.execute(
            select(WorkflowORM).where(WorkflowORM.status == WorkflowStatus.IN_PROGRESS.value)
        )
        orm_objs = result.scalars().all()
        return [self._to_domain(obj) for obj in orm_objs]

    @staticmethod
    def _to_domain(orm_obj: WorkflowORM) -> Workflow:
        # Convert string UUIDs back to UUID objects
        task_ids = [UUID(tid) for tid in orm_obj.task_ids]

        return Workflow(
            id=orm_obj.id,
            name=orm_obj.name,
            description=orm_obj.description,
            status=WorkflowStatus(orm_obj.status),
            task_ids=task_ids,
            metadata=orm_obj.metadata_,
            created_at=orm_obj.created_at,
            started_at=orm_obj.started_at,
            completed_at=orm_obj.completed_at,
            updated_at=orm_obj.updated_at,
        )

    @staticmethod
    def _from_domain(workflow: Workflow) -> WorkflowORM:
        # Convert UUID objects to strings for JSON storage
        task_ids_str = [str(tid) for tid in workflow.task_ids]

        return WorkflowORM(
            id=workflow.id,
            name=workflow.name,
            description=workflow.description,
            status=workflow.status.value,
            task_ids=task_ids_str,
            metadata_=workflow.metadata,
            created_at=workflow.created_at,
            started_at=workflow.started_at,
            completed_at=workflow.completed_at,
            updated_at=workflow.updated_at,
        )

    @staticmethod
    def _update_orm(orm_obj: WorkflowORM, workflow: Workflow) -> None:
        task_ids_str = [str(tid) for tid in workflow.task_ids]

        orm_obj.name = workflow.name
        orm_obj.description = workflow.description
        orm_obj.status = workflow.status.value
        orm_obj.task_ids = task_ids_str
        orm_obj.metadata_ = workflow.metadata
        orm_obj.started_at = workflow.started_at
        orm_obj.completed_at = workflow.completed_at
        orm_obj.updated_at = workflow.updated_at
