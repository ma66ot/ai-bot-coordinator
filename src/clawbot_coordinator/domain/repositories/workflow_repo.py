"""
Workflow repository interface (Port).

Abstract interface for workflow persistence operations.
"""
from abc import ABC, abstractmethod
from uuid import UUID

from ..models.workflow import Workflow


class WorkflowRepository(ABC):
    """Abstract repository for Workflow persistence operations."""

    @abstractmethod
    async def get(self, workflow_id: UUID) -> Workflow | None:
        """
        Fetch workflow by ID.

        Args:
            workflow_id: Unique identifier of the workflow

        Returns:
            Workflow if found, None otherwise
        """
        pass

    @abstractmethod
    async def save(self, workflow: Workflow) -> None:
        """
        Persist a workflow (insert or update).

        Args:
            workflow: Workflow domain model to persist
        """
        pass

    @abstractmethod
    async def delete(self, workflow_id: UUID) -> bool:
        """
        Delete a workflow by ID.

        Args:
            workflow_id: Unique identifier of the workflow

        Returns:
            True if workflow was deleted, False if not found
        """
        pass

    @abstractmethod
    async def get_all(self, skip: int = 0, limit: int = 100) -> list[Workflow]:
        """
        Fetch all workflows with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Workflow domain models
        """
        pass

    @abstractmethod
    async def get_by_status(self, status: str) -> list[Workflow]:
        """
        Find all workflows with a specific status.

        Args:
            status: Workflow status

        Returns:
            List of workflows with the specified status
        """
        pass

    @abstractmethod
    async def get_active_workflows(self) -> list[Workflow]:
        """
        Find all active (in-progress) workflows.

        Returns:
            List of workflows currently in progress
        """
        pass
