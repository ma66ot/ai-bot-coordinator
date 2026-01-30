"""
Feature tests for Bot API endpoints.

Tests full HTTP request/response cycle with real database.
Uses SQLite in-memory for speed - PostgreSQL-specific features tested separately.
"""
from uuid import UUID

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestBotRegistration:
    """Test bot registration endpoint."""

    async def test_register_bot_returns_201(
        self, client: AsyncClient, sample_bot_data: dict
    ) -> None:
        """Should create bot and return 201 with bot data."""
        response = await client.post("/api/v1/bots", json=sample_bot_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "test-bot"
        assert data["capabilities"] == ["python", "docker"]
        assert data["status"] == "offline"
        assert "id" in data
        assert UUID(data["id"])  # Validate UUID format

    async def test_register_bot_with_empty_name_fails(
        self, client: AsyncClient
    ) -> None:
        """Should reject bot with empty name."""
        response = await client.post(
            "/api/v1/bots",
            json={"name": "", "capabilities": ["python"]},
        )

        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
class TestBotRetrieval:
    """Test bot retrieval endpoints."""

    async def test_get_bot_by_id(
        self, client: AsyncClient, sample_bot_data: dict
    ) -> None:
        """Should retrieve bot by ID."""
        # Create bot first
        create_response = await client.post("/api/v1/bots", json=sample_bot_data)
        bot_id = create_response.json()["id"]

        # Get bot
        response = await client.get(f"/api/v1/bots/{bot_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == bot_id
        assert data["name"] == "test-bot"

    async def test_get_nonexistent_bot_returns_404(
        self, client: AsyncClient
    ) -> None:
        """Should return 404 for nonexistent bot."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.get(f"/api/v1/bots/{fake_id}")

        assert response.status_code == 404

    async def test_list_bots_returns_all_bots(
        self, client: AsyncClient, sample_bot_data: dict
    ) -> None:
        """Should return list of all bots."""
        # Create multiple bots
        await client.post("/api/v1/bots", json=sample_bot_data)
        await client.post(
            "/api/v1/bots",
            json={"name": "bot2", "capabilities": ["rust"]},
        )

        # List bots
        response = await client.get("/api/v1/bots")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2


@pytest.mark.asyncio
class TestBotHeartbeat:
    """Test bot heartbeat endpoint."""

    async def test_heartbeat_updates_last_seen(
        self, client: AsyncClient, sample_bot_data: dict
    ) -> None:
        """Should update last_seen and set status to online."""
        # Create bot
        create_response = await client.post("/api/v1/bots", json=sample_bot_data)
        bot_id = create_response.json()["id"]

        # Send heartbeat
        response = await client.post(f"/api/v1/bots/{bot_id}/heartbeat")

        assert response.status_code == 200
        data = response.json()
        assert data["bot_id"] == bot_id
        assert data["status"] == "online"
        assert data["last_seen"] is not None

    async def test_heartbeat_for_nonexistent_bot_returns_404(
        self, client: AsyncClient
    ) -> None:
        """Should return 404 for nonexistent bot."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.post(f"/api/v1/bots/{fake_id}/heartbeat")

        assert response.status_code == 404


@pytest.mark.asyncio
class TestBotStatusTransitions:
    """Test bot status transition endpoints."""

    async def test_mark_bot_busy(
        self, client: AsyncClient, sample_bot_data: dict
    ) -> None:
        """Should transition bot from online to busy."""
        # Create and go online
        create_response = await client.post("/api/v1/bots", json=sample_bot_data)
        bot_id = create_response.json()["id"]
        await client.post(f"/api/v1/bots/{bot_id}/heartbeat")

        # Mark busy
        response = await client.post(f"/api/v1/bots/{bot_id}/busy")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "busy"

    async def test_mark_offline_bot_busy_fails(
        self, client: AsyncClient, sample_bot_data: dict
    ) -> None:
        """Should fail to mark offline bot as busy."""
        create_response = await client.post("/api/v1/bots", json=sample_bot_data)
        bot_id = create_response.json()["id"]

        response = await client.post(f"/api/v1/bots/{bot_id}/busy")

        assert response.status_code == 400

    async def test_mark_bot_available(
        self, client: AsyncClient, sample_bot_data: dict
    ) -> None:
        """Should transition bot back to online."""
        # Create, go online, go busy
        create_response = await client.post("/api/v1/bots", json=sample_bot_data)
        bot_id = create_response.json()["id"]
        await client.post(f"/api/v1/bots/{bot_id}/heartbeat")
        await client.post(f"/api/v1/bots/{bot_id}/busy")

        # Mark available
        response = await client.post(f"/api/v1/bots/{bot_id}/available")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"


@pytest.mark.asyncio
class TestBotQueries:
    """Test bot query endpoints."""

    async def test_get_bots_by_capability(
        self, client: AsyncClient
    ) -> None:
        """Should return only bots with specified capability."""
        # Create bots with different capabilities
        await client.post(
            "/api/v1/bots",
            json={"name": "bot1", "capabilities": ["python", "docker"]},
        )
        await client.post(
            "/api/v1/bots",
            json={"name": "bot2", "capabilities": ["rust", "kubernetes"]},
        )
        await client.post(
            "/api/v1/bots",
            json={"name": "bot3", "capabilities": ["python", "rust"]},
        )

        # Query by capability
        response = await client.get("/api/v1/bots/capability/python")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        for bot in data:
            assert "python" in bot["capabilities"]

    async def test_get_available_bots(
        self, client: AsyncClient
    ) -> None:
        """Should return only online bots."""
        # Create bots
        response1 = await client.post(
            "/api/v1/bots",
            json={"name": "bot1", "capabilities": ["python"]},
        )
        response2 = await client.post(
            "/api/v1/bots",
            json={"name": "bot2", "capabilities": ["python"]},
        )

        bot1_id = response1.json()["id"]
        bot2_id = response2.json()["id"]

        # Only bot1 goes online
        await client.post(f"/api/v1/bots/{bot1_id}/heartbeat")

        # Query available bots
        response = await client.get("/api/v1/bots/available/")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == bot1_id


@pytest.mark.asyncio
class TestBotDeletion:
    """Test bot deletion endpoint."""

    async def test_delete_bot(
        self, client: AsyncClient, sample_bot_data: dict
    ) -> None:
        """Should delete bot and return 204."""
        # Create bot
        create_response = await client.post("/api/v1/bots", json=sample_bot_data)
        bot_id = create_response.json()["id"]

        # Delete bot
        response = await client.delete(f"/api/v1/bots/{bot_id}")

        assert response.status_code == 204

        # Verify bot is gone
        get_response = await client.get(f"/api/v1/bots/{bot_id}")
        assert get_response.status_code == 404

    async def test_delete_nonexistent_bot_returns_404(
        self, client: AsyncClient
    ) -> None:
        """Should return 404 when deleting nonexistent bot."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.delete(f"/api/v1/bots/{fake_id}")

        assert response.status_code == 404
