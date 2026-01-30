"""
Unit tests for Bot domain model.

Tests state machine behavior, validation rules, and business logic
without any database dependencies.
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError as PydanticValidationError

from clawbot_coordinator.domain.models.bot import Bot, BotStatus
from clawbot_coordinator.exceptions import InvalidStateTransition


class TestBotCreation:
    """Test Bot model instantiation and defaults."""

    def test_create_bot_with_minimal_fields(self) -> None:
        """Should create bot with only required fields."""
        bot = Bot(name="test-bot", capabilities=["python", "docker"])

        assert bot.name == "test-bot"
        assert bot.capabilities == ["python", "docker"]
        assert bot.status == BotStatus.OFFLINE
        assert bot.id is not None
        assert isinstance(bot.created_at, datetime)
        assert isinstance(bot.updated_at, datetime)
        assert bot.last_seen is None

    def test_create_bot_with_all_fields(self) -> None:
        """Should create bot with all fields specified."""
        bot_id = uuid4()
        now = datetime.now(timezone.utc)

        bot = Bot(
            id=bot_id,
            name="full-bot",
            capabilities=["rust", "kubernetes"],
            status=BotStatus.ONLINE,
            last_seen=now,
            metadata={"version": "1.0", "region": "us-west"},
            created_at=now,
            updated_at=now,
        )

        assert bot.id == bot_id
        assert bot.name == "full-bot"
        assert bot.status == BotStatus.ONLINE
        assert bot.last_seen == now
        assert bot.metadata == {"version": "1.0", "region": "us-west"}

    def test_bot_name_must_not_be_empty(self) -> None:
        """Should reject empty bot names."""
        with pytest.raises(PydanticValidationError) as exc_info:
            Bot(name="", capabilities=["python"])

        assert "name" in str(exc_info.value).lower()

    def test_bot_must_have_at_least_one_capability(self) -> None:
        """Should reject bots with no capabilities."""
        with pytest.raises(PydanticValidationError) as exc_info:
            Bot(name="no-skills-bot", capabilities=[])

        assert "capabilities" in str(exc_info.value).lower()


class TestBotStatusTransitions:
    """Test state machine for bot status changes."""

    def test_go_online_from_offline(self) -> None:
        """Should transition offline -> online."""
        bot = Bot(name="bot", capabilities=["test"])
        assert bot.status == BotStatus.OFFLINE

        bot.go_online()

        assert bot.status == BotStatus.ONLINE
        assert bot.last_seen is not None

    def test_go_busy_from_online(self) -> None:
        """Should transition online -> busy."""
        bot = Bot(name="bot", capabilities=["test"])
        bot.go_online()

        bot.go_busy()

        assert bot.status == BotStatus.BUSY

    def test_go_busy_from_offline_fails(self) -> None:
        """Should not allow offline -> busy transition."""
        bot = Bot(name="bot", capabilities=["test"])
        assert bot.status == BotStatus.OFFLINE

        with pytest.raises(InvalidStateTransition) as exc_info:
            bot.go_busy()

        assert "offline" in str(exc_info.value).lower()
        assert "busy" in str(exc_info.value).lower()

    def test_go_offline_from_any_state(self) -> None:
        """Should allow transition to offline from any state."""
        bot = Bot(name="bot", capabilities=["test"])

        # From offline -> offline (no-op but allowed)
        bot.go_offline()
        assert bot.status == BotStatus.OFFLINE

        # From online -> offline
        bot.go_online()
        bot.go_offline()
        assert bot.status == BotStatus.OFFLINE

        # From busy -> offline
        bot.go_online()
        bot.go_busy()
        bot.go_offline()
        assert bot.status == BotStatus.OFFLINE

    def test_go_online_from_busy(self) -> None:
        """Should transition busy -> online when task completes."""
        bot = Bot(name="bot", capabilities=["test"])
        bot.go_online()
        bot.go_busy()

        bot.go_online()

        assert bot.status == BotStatus.ONLINE


class TestBotHeartbeat:
    """Test heartbeat functionality."""

    def test_heartbeat_updates_last_seen(self) -> None:
        """Should update last_seen timestamp on heartbeat."""
        bot = Bot(name="bot", capabilities=["test"])
        original_last_seen = bot.last_seen

        bot.heartbeat()

        assert bot.last_seen is not None
        assert bot.last_seen != original_last_seen

    def test_heartbeat_sets_online_if_offline(self) -> None:
        """Should automatically go online on heartbeat if offline."""
        bot = Bot(name="bot", capabilities=["test"])
        assert bot.status == BotStatus.OFFLINE

        bot.heartbeat()

        assert bot.status == BotStatus.ONLINE
        assert bot.last_seen is not None

    def test_heartbeat_updates_updated_at(self) -> None:
        """Should update the updated_at timestamp."""
        bot = Bot(name="bot", capabilities=["test"])
        original_updated = bot.updated_at

        bot.heartbeat()

        assert bot.updated_at > original_updated


class TestBotCapabilities:
    """Test capability-related methods."""

    def test_has_capability_returns_true_when_present(self) -> None:
        """Should return True for capabilities the bot has."""
        bot = Bot(name="bot", capabilities=["python", "docker", "rust"])

        assert bot.has_capability("python") is True
        assert bot.has_capability("docker") is True
        assert bot.has_capability("rust") is True

    def test_has_capability_returns_false_when_absent(self) -> None:
        """Should return False for capabilities the bot lacks."""
        bot = Bot(name="bot", capabilities=["python"])

        assert bot.has_capability("java") is False
        assert bot.has_capability("go") is False

    def test_has_capability_is_case_sensitive(self) -> None:
        """Should treat capabilities as case-sensitive."""
        bot = Bot(name="bot", capabilities=["Python"])

        assert bot.has_capability("Python") is True
        assert bot.has_capability("python") is False


class TestBotAvailability:
    """Test bot availability checks."""

    def test_is_available_true_when_online(self) -> None:
        """Should be available when status is online."""
        bot = Bot(name="bot", capabilities=["test"])
        bot.go_online()

        assert bot.is_available() is True

    def test_is_available_false_when_offline(self) -> None:
        """Should not be available when offline."""
        bot = Bot(name="bot", capabilities=["test"])

        assert bot.is_available() is False

    def test_is_available_false_when_busy(self) -> None:
        """Should not be available when busy."""
        bot = Bot(name="bot", capabilities=["test"])
        bot.go_online()
        bot.go_busy()

        assert bot.is_available() is False

    def test_is_stale_returns_true_after_timeout(self) -> None:
        """Should detect stale bots that haven't sent heartbeat recently."""
        bot = Bot(name="bot", capabilities=["test"])
        bot.go_online()

        # Simulate old heartbeat
        old_time = datetime.now(timezone.utc) - timedelta(seconds=150)
        bot.last_seen = old_time

        assert bot.is_stale(timeout_seconds=60) is True

    def test_is_stale_returns_false_when_recent(self) -> None:
        """Should not be stale when heartbeat is recent."""
        bot = Bot(name="bot", capabilities=["test"])
        bot.heartbeat()

        assert bot.is_stale(timeout_seconds=60) is False

    def test_is_stale_returns_true_when_never_seen(self) -> None:
        """Should be stale if never received heartbeat."""
        bot = Bot(name="bot", capabilities=["test"])
        assert bot.last_seen is None

        assert bot.is_stale(timeout_seconds=60) is True
