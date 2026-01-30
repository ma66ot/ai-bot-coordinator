"""
Unit tests for BotService.

Tests business logic with mocked repository - no database required.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from clawbot_coordinator.domain.models.bot import Bot, BotStatus
from clawbot_coordinator.domain.repositories.bot_repo import BotRepository
from clawbot_coordinator.domain.services.bot_service import BotService
from clawbot_coordinator.exceptions import ResourceNotFound


@pytest.fixture
def mock_repo() -> AsyncMock:
    """Create a mocked BotRepository."""
    return AsyncMock(spec=BotRepository)


@pytest.fixture
def service(mock_repo: AsyncMock) -> BotService:
    """Create BotService with mocked repository."""
    return BotService(repository=mock_repo)


class TestRegisterBot:
    """Test bot registration."""

    async def test_register_bot_creates_new_bot(
        self, service: BotService, mock_repo: AsyncMock
    ) -> None:
        """Should create and save a new bot."""
        mock_repo.save = AsyncMock()

        bot = await service.register_bot(
            name="test-bot",
            capabilities=["python", "docker"],
        )

        assert bot.name == "test-bot"
        assert bot.capabilities == ["python", "docker"]
        assert bot.status == BotStatus.OFFLINE
        mock_repo.save.assert_called_once()

    async def test_register_bot_with_metadata(
        self, service: BotService, mock_repo: AsyncMock
    ) -> None:
        """Should accept metadata during registration."""
        mock_repo.save = AsyncMock()

        bot = await service.register_bot(
            name="test-bot",
            capabilities=["rust"],
            metadata={"version": "1.0", "region": "us-west"},
        )

        assert bot.metadata == {"version": "1.0", "region": "us-west"}
        mock_repo.save.assert_called_once()


class TestHeartbeat:
    """Test heartbeat functionality."""

    async def test_heartbeat_updates_existing_bot(
        self, service: BotService, mock_repo: AsyncMock
    ) -> None:
        """Should update last_seen and set bot online."""
        bot_id = uuid4()
        existing_bot = Bot(name="test", capabilities=["test"])
        existing_bot.id = bot_id

        mock_repo.get = AsyncMock(return_value=existing_bot)
        mock_repo.save = AsyncMock()

        await service.heartbeat(bot_id)

        mock_repo.get.assert_called_once_with(bot_id)
        mock_repo.save.assert_called_once()

        # Verify bot was updated
        saved_bot = mock_repo.save.call_args[0][0]
        assert saved_bot.status == BotStatus.ONLINE
        assert saved_bot.last_seen is not None

    async def test_heartbeat_raises_if_bot_not_found(
        self, service: BotService, mock_repo: AsyncMock
    ) -> None:
        """Should raise ResourceNotFound if bot doesn't exist."""
        bot_id = uuid4()
        mock_repo.get = AsyncMock(return_value=None)

        with pytest.raises(ResourceNotFound) as exc_info:
            await service.heartbeat(bot_id)

        assert "Bot" in str(exc_info.value)
        assert str(bot_id) in str(exc_info.value)


class TestGetBot:
    """Test getting bot by ID."""

    async def test_get_bot_returns_existing_bot(
        self, service: BotService, mock_repo: AsyncMock
    ) -> None:
        """Should return bot if found."""
        bot_id = uuid4()
        bot = Bot(id=bot_id, name="test", capabilities=["test"])
        mock_repo.get = AsyncMock(return_value=bot)

        result = await service.get_bot(bot_id)

        assert result == bot
        mock_repo.get.assert_called_once_with(bot_id)

    async def test_get_bot_raises_if_not_found(
        self, service: BotService, mock_repo: AsyncMock
    ) -> None:
        """Should raise ResourceNotFound if bot doesn't exist."""
        bot_id = uuid4()
        mock_repo.get = AsyncMock(return_value=None)

        with pytest.raises(ResourceNotFound):
            await service.get_bot(bot_id)


class TestGetByCapability:
    """Test finding bots by capability."""

    async def test_get_by_capability_returns_matching_bots(
        self, service: BotService, mock_repo: AsyncMock
    ) -> None:
        """Should return all bots with the capability."""
        bots = [
            Bot(name="bot1", capabilities=["python", "docker"]),
            Bot(name="bot2", capabilities=["python", "rust"]),
        ]
        mock_repo.get_by_capability = AsyncMock(return_value=bots)

        result = await service.get_by_capability("python")

        assert len(result) == 2
        mock_repo.get_by_capability.assert_called_once_with("python")

    async def test_get_by_capability_returns_empty_if_none_found(
        self, service: BotService, mock_repo: AsyncMock
    ) -> None:
        """Should return empty list if no bots have the capability."""
        mock_repo.get_by_capability = AsyncMock(return_value=[])

        result = await service.get_by_capability("cobol")

        assert result == []


class TestGetAvailableBots:
    """Test getting available bots."""

    async def test_get_available_bots_without_capability_filter(
        self, service: BotService, mock_repo: AsyncMock
    ) -> None:
        """Should return all online bots."""
        bots = [
            Bot(name="bot1", capabilities=["python"]),
            Bot(name="bot2", capabilities=["rust"]),
        ]
        for bot in bots:
            bot.go_online()

        mock_repo.get_available_bots = AsyncMock(return_value=bots)

        result = await service.get_available_bots()

        assert len(result) == 2
        mock_repo.get_available_bots.assert_called_once_with(None)

    async def test_get_available_bots_with_capability_filter(
        self, service: BotService, mock_repo: AsyncMock
    ) -> None:
        """Should return only online bots with the specified capability."""
        bot = Bot(name="bot1", capabilities=["python"])
        bot.go_online()

        mock_repo.get_available_bots = AsyncMock(return_value=[bot])

        result = await service.get_available_bots(capability="python")

        assert len(result) == 1
        assert result[0].has_capability("python")
        mock_repo.get_available_bots.assert_called_once_with("python")


class TestMarkBotBusy:
    """Test marking bot as busy."""

    async def test_mark_bot_busy_transitions_to_busy(
        self, service: BotService, mock_repo: AsyncMock
    ) -> None:
        """Should transition online bot to busy."""
        bot_id = uuid4()
        bot = Bot(id=bot_id, name="test", capabilities=["test"])
        bot.go_online()

        mock_repo.get = AsyncMock(return_value=bot)
        mock_repo.save = AsyncMock()

        await service.mark_bot_busy(bot_id)

        mock_repo.get.assert_called_once_with(bot_id)
        mock_repo.save.assert_called_once()

        saved_bot = mock_repo.save.call_args[0][0]
        assert saved_bot.status == BotStatus.BUSY


class TestMarkBotAvailable:
    """Test marking bot as available."""

    async def test_mark_bot_available_transitions_to_online(
        self, service: BotService, mock_repo: AsyncMock
    ) -> None:
        """Should transition busy bot back to online."""
        bot_id = uuid4()
        bot = Bot(id=bot_id, name="test", capabilities=["test"])
        bot.go_online()
        bot.go_busy()

        mock_repo.get = AsyncMock(return_value=bot)
        mock_repo.save = AsyncMock()

        await service.mark_bot_available(bot_id)

        saved_bot = mock_repo.save.call_args[0][0]
        assert saved_bot.status == BotStatus.ONLINE


class TestListBots:
    """Test listing all bots."""

    async def test_list_bots_with_pagination(
        self, service: BotService, mock_repo: AsyncMock
    ) -> None:
        """Should pass pagination parameters to repository."""
        bots = [Bot(name=f"bot{i}", capabilities=["test"]) for i in range(5)]
        mock_repo.get_all = AsyncMock(return_value=bots)

        result = await service.list_bots(skip=10, limit=50)

        assert len(result) == 5
        mock_repo.get_all.assert_called_once_with(skip=10, limit=50)
