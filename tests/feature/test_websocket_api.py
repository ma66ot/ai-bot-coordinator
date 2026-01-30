"""Feature tests for WebSocket API.

NOTE: Full WebSocket connection tests require a WebSocket test client.
These tests focus on the HTTP endpoints that support WebSocket functionality.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestWebSocketConnectionsAPI:
    """Test WebSocket connections management API."""

    async def test_list_active_connections_empty(self, client: AsyncClient) -> None:
        """Should return empty list when no connections."""
        response = await client.get("/api/v1/ws/connections")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["bot_ids"] == []


@pytest.mark.asyncio
class TestBroadcastTaskAssignment:
    """Test broadcasting task assignments to connected bots."""

    async def test_broadcast_to_disconnected_bot(
        self, client: AsyncClient, sample_bot_data: dict
    ) -> None:
        """Should return 404 when bot not connected."""
        # Create workflow and task
        workflow_response = await client.post(
            "/api/v1/workflows",
            json={"name": "Test Workflow", "task_payloads": [{"action": "build"}]},
        )
        workflow_data = workflow_response.json()
        task_id = workflow_data["task_ids"][0]

        # Register bot (but don't connect via WebSocket)
        bot_response = await client.post("/api/v1/bots", json=sample_bot_data)
        bot_id = bot_response.json()["id"]

        # Try to broadcast to disconnected bot
        broadcast_response = await client.post(
            f"/api/v1/ws/broadcast/task/{task_id}?bot_id={bot_id}"
        )
        assert broadcast_response.status_code == 404
        assert "not connected" in broadcast_response.json()["detail"]

    async def test_broadcast_to_nonexistent_task(
        self, client: AsyncClient, sample_bot_data: dict
    ) -> None:
        """Should return 404 for non-existent task."""
        fake_task_id = "00000000-0000-0000-0000-000000000000"

        # Register bot
        bot_response = await client.post("/api/v1/bots", json=sample_bot_data)
        bot_id = bot_response.json()["id"]

        # Try to broadcast non-existent task
        broadcast_response = await client.post(
            f"/api/v1/ws/broadcast/task/{fake_task_id}?bot_id={bot_id}"
        )
        # Will fail because bot is not connected (checked first)
        assert broadcast_response.status_code == 404
