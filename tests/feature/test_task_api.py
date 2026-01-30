"""
Feature tests for Task API endpoints.

Tests full HTTP request/response cycle with real database.
"""
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestTaskCreation:
    """Test task creation endpoint."""

    async def test_create_task_returns_201(
        self, client: AsyncClient
    ) -> None:
        """Should create task and return 201 with task data."""
        workflow_id = uuid4()
        task_data = {
            "workflow_id": str(workflow_id),
            "payload": {"action": "deploy", "target": "production"},
            "timeout_seconds": 600,
        }

        response = await client.post("/api/v1/tasks", json=task_data)

        assert response.status_code == 201
        data = response.json()
        assert data["workflow_id"] == str(workflow_id)
        assert data["status"] == "pending"
        assert data["timeout_seconds"] == 600
        assert "id" in data
        assert UUID(data["id"])


@pytest.mark.asyncio
class TestTaskRetrieval:
    """Test task retrieval endpoints."""

    async def test_get_task_by_id(
        self, client: AsyncClient
    ) -> None:
        """Should retrieve task by ID."""
        # Create task first
        create_response = await client.post(
            "/api/v1/tasks",
            json={"workflow_id": str(uuid4()), "payload": {"test": "data"}},
        )
        task_id = create_response.json()["id"]

        # Get task
        response = await client.get(f"/api/v1/tasks/{task_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == task_id

    async def test_list_tasks_returns_all_tasks(
        self, client: AsyncClient
    ) -> None:
        """Should return list of all tasks."""
        # Create multiple tasks
        await client.post(
            "/api/v1/tasks",
            json={"workflow_id": str(uuid4()), "payload": {}},
        )
        await client.post(
            "/api/v1/tasks",
            json={"workflow_id": str(uuid4()), "payload": {}},
        )

        # List tasks
        response = await client.get("/api/v1/tasks")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 2


@pytest.mark.asyncio
class TestTaskAssignment:
    """Test task assignment endpoint."""

    async def test_assign_task_to_bot(
        self, client: AsyncClient, sample_bot_data: dict
    ) -> None:
        """Should assign task to bot."""
        # Create bot
        bot_response = await client.post("/api/v1/bots", json=sample_bot_data)
        bot_id = bot_response.json()["id"]

        # Create task
        task_response = await client.post(
            "/api/v1/tasks",
            json={"workflow_id": str(uuid4()), "payload": {}},
        )
        task_id = task_response.json()["id"]

        # Assign task
        response = await client.post(
            f"/api/v1/tasks/{task_id}/assign",
            json={"bot_id": bot_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "assigned"
        assert data["message"] == "Task assigned to bot"

        # Verify task is assigned
        task = await client.get(f"/api/v1/tasks/{task_id}")
        assert task.json()["bot_id"] == bot_id


@pytest.mark.asyncio
class TestTaskLifecycle:
    """Test complete task lifecycle."""

    async def test_full_task_lifecycle_success(
        self, client: AsyncClient, sample_bot_data: dict
    ) -> None:
        """Should complete full task lifecycle: create→assign→start→complete."""
        # Create bot
        bot_response = await client.post("/api/v1/bots", json=sample_bot_data)
        bot_id = bot_response.json()["id"]

        # Create task
        task_response = await client.post(
            "/api/v1/tasks",
            json={"workflow_id": str(uuid4()), "payload": {"action": "test"}},
        )
        task_id = task_response.json()["id"]
        assert task_response.json()["status"] == "pending"

        # Assign to bot
        assign_response = await client.post(
            f"/api/v1/tasks/{task_id}/assign",
            json={"bot_id": bot_id},
        )
        assert assign_response.status_code == 200
        assert assign_response.json()["status"] == "assigned"

        # Start task
        start_response = await client.post(f"/api/v1/tasks/{task_id}/start")
        assert start_response.status_code == 200
        assert start_response.json()["status"] == "in_progress"

        # Complete task
        complete_response = await client.post(
            f"/api/v1/tasks/{task_id}/complete",
            json={"result": {"output": "success", "duration": 5.2}},
        )
        assert complete_response.status_code == 200
        assert complete_response.json()["status"] == "completed"

        # Verify final state
        final_task = await client.get(f"/api/v1/tasks/{task_id}")
        final_data = final_task.json()
        assert final_data["status"] == "completed"
        assert final_data["result"]["output"] == "success"

    async def test_full_task_lifecycle_failure(
        self, client: AsyncClient, sample_bot_data: dict
    ) -> None:
        """Should handle task failure."""
        # Create bot and task
        bot_response = await client.post("/api/v1/bots", json=sample_bot_data)
        bot_id = bot_response.json()["id"]

        task_response = await client.post(
            "/api/v1/tasks",
            json={"workflow_id": str(uuid4()), "payload": {}},
        )
        task_id = task_response.json()["id"]

        # Assign and start
        await client.post(f"/api/v1/tasks/{task_id}/assign", json={"bot_id": bot_id})
        await client.post(f"/api/v1/tasks/{task_id}/start")

        # Fail task
        fail_response = await client.post(
            f"/api/v1/tasks/{task_id}/fail",
            json={"result": {"error": "Connection timeout", "code": "ERR_TIMEOUT"}},
        )
        assert fail_response.status_code == 200
        assert fail_response.json()["status"] == "failed"

        # Verify final state
        final_task = await client.get(f"/api/v1/tasks/{task_id}")
        assert final_task.json()["status"] == "failed"
        assert final_task.json()["result"]["error"] == "Connection timeout"


@pytest.mark.asyncio
class TestTaskStateTransitions:
    """Test state transition validation."""

    async def test_cannot_start_pending_task(
        self, client: AsyncClient
    ) -> None:
        """Should not allow starting a pending task."""
        task_response = await client.post(
            "/api/v1/tasks",
            json={"workflow_id": str(uuid4()), "payload": {}},
        )
        task_id = task_response.json()["id"]

        response = await client.post(f"/api/v1/tasks/{task_id}/start")

        assert response.status_code == 400

    async def test_cannot_complete_unstarted_task(
        self, client: AsyncClient
    ) -> None:
        """Should not allow completing a task that hasn't started."""
        task_response = await client.post(
            "/api/v1/tasks",
            json={"workflow_id": str(uuid4()), "payload": {}},
        )
        task_id = task_response.json()["id"]

        response = await client.post(
            f"/api/v1/tasks/{task_id}/complete",
            json={"result": {"output": "done"}},
        )

        assert response.status_code == 400


@pytest.mark.asyncio
class TestTaskCancellation:
    """Test task cancellation."""

    async def test_cancel_task(
        self, client: AsyncClient
    ) -> None:
        """Should cancel task from any state."""
        task_response = await client.post(
            "/api/v1/tasks",
            json={"workflow_id": str(uuid4()), "payload": {}},
        )
        task_id = task_response.json()["id"]

        response = await client.post(f"/api/v1/tasks/{task_id}/cancel")

        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"


@pytest.mark.asyncio
class TestTaskQueries:
    """Test task query endpoints."""

    async def test_get_tasks_by_workflow(
        self, client: AsyncClient
    ) -> None:
        """Should return tasks for specific workflow."""
        workflow_id = uuid4()

        # Create tasks for same workflow
        await client.post(
            "/api/v1/tasks",
            json={"workflow_id": str(workflow_id), "payload": {}},
        )
        await client.post(
            "/api/v1/tasks",
            json={"workflow_id": str(workflow_id), "payload": {}},
        )

        # Create task for different workflow
        await client.post(
            "/api/v1/tasks",
            json={"workflow_id": str(uuid4()), "payload": {}},
        )

        # Query by workflow
        response = await client.get(f"/api/v1/tasks/workflow/{workflow_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        for task in data:
            assert task["workflow_id"] == str(workflow_id)

    async def test_get_tasks_by_bot(
        self, client: AsyncClient, sample_bot_data: dict
    ) -> None:
        """Should return tasks assigned to specific bot."""
        # Create bot
        bot_response = await client.post("/api/v1/bots", json=sample_bot_data)
        bot_id = bot_response.json()["id"]

        # Create and assign tasks
        task1_response = await client.post(
            "/api/v1/tasks",
            json={"workflow_id": str(uuid4()), "payload": {}},
        )
        task1_id = task1_response.json()["id"]
        await client.post(f"/api/v1/tasks/{task1_id}/assign", json={"bot_id": bot_id})

        task2_response = await client.post(
            "/api/v1/tasks",
            json={"workflow_id": str(uuid4()), "payload": {}},
        )
        task2_id = task2_response.json()["id"]
        await client.post(f"/api/v1/tasks/{task2_id}/assign", json={"bot_id": bot_id})

        # Query by bot
        response = await client.get(f"/api/v1/tasks/bot/{bot_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    async def test_get_pending_tasks(
        self, client: AsyncClient
    ) -> None:
        """Should return only pending tasks."""
        # Create pending task
        await client.post(
            "/api/v1/tasks",
            json={"workflow_id": str(uuid4()), "payload": {}},
        )

        # Query pending tasks
        response = await client.get("/api/v1/tasks/status/pending")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        for task in data:
            assert task["status"] == "pending"


@pytest.mark.asyncio
class TestTaskDeletion:
    """Test task deletion endpoint."""

    async def test_delete_task(
        self, client: AsyncClient
    ) -> None:
        """Should delete task and return 204."""
        task_response = await client.post(
            "/api/v1/tasks",
            json={"workflow_id": str(uuid4()), "payload": {}},
        )
        task_id = task_response.json()["id"]

        response = await client.delete(f"/api/v1/tasks/{task_id}")

        assert response.status_code == 204

        # Verify task is gone
        get_response = await client.get(f"/api/v1/tasks/{task_id}")
        assert get_response.status_code == 404
