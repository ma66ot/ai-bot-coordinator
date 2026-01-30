"""
Workflow service - orchestration logic for managing workflows and task sequencing.

Coordinates workflows, tasks, and bot assignment.
"""
from typing import Any
from uuid import UUID

from ..models.task import TaskStatus
from ..models.workflow import Workflow
from ..repositories.bot_repo import BotRepository
from ..repositories.task_repo import TaskRepository
from ..repositories.workflow_repo import WorkflowRepository
from ...exceptions import ResourceNotFound


class WorkflowService:
    """Service layer for workflow orchestration."""

    def __init__(
        self,
        workflow_repo: WorkflowRepository,
        task_repo: TaskRepository,
        bot_repo: BotRepository,
    ) -> None:
        self._workflow_repo = workflow_repo
        self._task_repo = task_repo
        self._bot_repo = bot_repo

    async def create_workflow(
        self,
        name: str,
        description: str = "",
        task_payloads: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Workflow:
        """
        Create a new workflow with optional tasks.

        Args:
            name: Workflow name
            description: Workflow description
            task_payloads: List of task payloads to create
            metadata: Workflow metadata

        Returns:
            Created workflow
        """
        workflow = Workflow(
            name=name,
            description=description,
            metadata=metadata or {},
        )

        # Create tasks if provided
        if task_payloads:
            from .task_service import TaskService

            task_service = TaskService(self._task_repo, self._bot_repo)
            for payload in task_payloads:
                task = await task_service.create_task(
                    workflow_id=workflow.id,
                    payload=payload,
                )
                workflow.add_task(task.id)

        await self._workflow_repo.save(workflow)
        return workflow

    async def start_workflow(self, workflow_id: UUID) -> None:
        """Start workflow execution."""
        workflow = await self._workflow_repo.get(workflow_id)
        if not workflow:
            raise ResourceNotFound("Workflow", str(workflow_id))

        workflow.start()
        await self._workflow_repo.save(workflow)

    async def get_workflow(self, workflow_id: UUID) -> Workflow:
        """Get workflow by ID."""
        workflow = await self._workflow_repo.get(workflow_id)
        if not workflow:
            raise ResourceNotFound("Workflow", str(workflow_id))
        return workflow

    async def get_workflow_with_tasks(self, workflow_id: UUID) -> tuple[Workflow, list]:
        """Get workflow with its tasks."""
        workflow = await self.get_workflow(workflow_id)
        tasks = await self._task_repo.get_by_workflow(workflow_id)
        return workflow, tasks

    async def list_workflows(self, skip: int = 0, limit: int = 100) -> list[Workflow]:
        """List all workflows."""
        return await self._workflow_repo.get_all(skip=skip, limit=limit)

    async def delete_workflow(self, workflow_id: UUID) -> None:
        """Delete a workflow."""
        deleted = await self._workflow_repo.delete(workflow_id)
        if not deleted:
            raise ResourceNotFound("Workflow", str(workflow_id))
