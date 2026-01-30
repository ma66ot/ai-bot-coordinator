"""Feature tests for Workflow API endpoints."""
from uuid import UUID

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestWorkflowCreation:
    """Test workflow creation endpoint."""

    async def test_create_workflow_without_tasks(
        self, client: AsyncClient
    ) -> None:
        """Should create workflow without tasks."""
        response = await client.post(
            "/api/v1/workflows",
            json={"name": "Test Workflow", "description": "A test workflow"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Workflow"
        assert data["status"] == "pending"
        assert data["task_ids"] == []
        assert UUID(data["id"])

    async def test_create_workflow_with_tasks(
        self, client: AsyncClient
    ) -> None:
        """Should create workflow with tasks."""
        response = await client.post(
            "/api/v1/workflows",
            json={
                "name": "Multi-Task Workflow",
                "task_payloads": [
                    {"action": "build", "target": "app"},
                    {"action": "test", "suite": "integration"},
                    {"action": "deploy", "environment": "staging"},
                ],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Multi-Task Workflow"
        assert len(data["task_ids"]) == 3


@pytest.mark.asyncio
class TestWorkflowRetrieval:
    """Test workflow retrieval endpoints."""

    async def test_get_workflow_by_id(
        self, client: AsyncClient
    ) -> None:
        """Should retrieve workflow by ID."""
        create_response = await client.post(
            "/api/v1/workflows",
            json={"name": "Test"},
        )
        workflow_id = create_response.json()["id"]

        response = await client.get(f"/api/v1/workflows/{workflow_id}")

        assert response.status_code == 200
        assert response.json()["id"] == workflow_id

    async def test_get_workflow_with_tasks(
        self, client: AsyncClient
    ) -> None:
        """Should retrieve workflow with embedded tasks."""
        create_response = await client.post(
            "/api/v1/workflows",
            json={
                "name": "Full Workflow",
                "task_payloads": [{"action": "task1"}, {"action": "task2"}],
            },
        )
        workflow_id = create_response.json()["id"]

        response = await client.get(f"/api/v1/workflows/{workflow_id}/tasks")

        assert response.status_code == 200
        data = response.json()
        assert data["workflow"]["id"] == workflow_id
        assert len(data["tasks"]) == 2

    async def test_list_workflows(
        self, client: AsyncClient
    ) -> None:
        """Should list all workflows."""
        await client.post("/api/v1/workflows", json={"name": "Workflow 1"})
        await client.post("/api/v1/workflows", json={"name": "Workflow 2"})

        response = await client.get("/api/v1/workflows")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2


@pytest.mark.asyncio
class TestWorkflowExecution:
    """Test workflow execution."""

    async def test_start_workflow(
        self, client: AsyncClient
    ) -> None:
        """Should start workflow."""
        create_response = await client.post(
            "/api/v1/workflows",
            json={"name": "Test"},
        )
        workflow_id = create_response.json()["id"]

        response = await client.post(f"/api/v1/workflows/{workflow_id}/start")

        assert response.status_code == 200
        assert response.json()["status"] == "in_progress"


@pytest.mark.asyncio
class TestWorkflowDeletion:
    """Test workflow deletion."""

    async def test_delete_workflow(
        self, client: AsyncClient
    ) -> None:
        """Should delete workflow."""
        create_response = await client.post(
            "/api/v1/workflows",
            json={"name": "To Delete"},
        )
        workflow_id = create_response.json()["id"]

        response = await client.delete(f"/api/v1/workflows/{workflow_id}")

        assert response.status_code == 204

        # Verify deleted
        get_response = await client.get(f"/api/v1/workflows/{workflow_id}")
        assert get_response.status_code == 404


@pytest.mark.asyncio
class TestFullSystemIntegration:
    """Test complete bot-task-workflow integration."""

    async def test_create_workflow_verify_tasks_created(
        self, client: AsyncClient
    ) -> None:
        """Should create workflow and all its tasks."""
        response = await client.post(
            "/api/v1/workflows",
            json={
                "name": "CI/CD Pipeline",
                "description": "Full deployment pipeline",
                "task_payloads": [
                    {"action": "build", "dockerfile": "Dockerfile"},
                    {"action": "test", "suite": "all"},
                    {"action": "deploy", "env": "production"},
                ],
                "metadata": {"project": "clawbot", "version": "1.0"},
            },
        )

        assert response.status_code == 201
        workflow_data = response.json()
        workflow_id = workflow_data["id"]
        task_ids = workflow_data["task_ids"]

        assert len(task_ids) == 3
        assert workflow_data["metadata"]["project"] == "clawbot"

        # Verify tasks exist
        for task_id in task_ids:
            task_response = await client.get(f"/api/v1/tasks/{task_id}")
            assert task_response.status_code == 200
            task_data = task_response.json()
            assert task_data["workflow_id"] == workflow_id
            assert task_data["status"] == "pending"
