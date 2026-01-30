"""
Bot domain model.

Represents a bot agent in the system with capabilities and status tracking.
This is a pure domain model using Pydantic - no SQLAlchemy dependencies.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ...exceptions import InvalidStateTransition, ValidationError


class BotStatus(str, Enum):
    """Valid states for a bot."""

    OFFLINE = "offline"
    ONLINE = "online"
    BUSY = "busy"


class Bot(BaseModel):
    """
    Bot domain model representing a worker agent.

    State machine transitions:
    - offline -> online (via go_online or heartbeat)
    - online -> busy (via go_busy)
    - busy -> online (via go_online)
    - any -> offline (via go_offline)
    """

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., min_length=1, max_length=255)
    capabilities: list[str] = Field(..., min_length=1)
    status: BotStatus = Field(default=BotStatus.OFFLINE)
    last_seen: datetime | None = Field(default=None)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure bot name is not empty or whitespace-only."""
        if not v or not v.strip():
            raise ValidationError("name", "Bot name cannot be empty")
        return v

    @field_validator("capabilities")
    @classmethod
    def validate_capabilities(cls, v: list[str]) -> list[str]:
        """Ensure bot has at least one capability."""
        if not v or len(v) == 0:
            raise ValidationError("capabilities", "Bot must have at least one capability")
        return v

    def go_online(self) -> None:
        """
        Transition bot to online status.

        Valid from: offline, busy
        Sets last_seen to current time.
        """
        self.status = BotStatus.ONLINE
        self.last_seen = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def go_busy(self) -> None:
        """
        Transition bot to busy status.

        Valid from: online only
        Raises InvalidStateTransition if not online.
        """
        if self.status != BotStatus.ONLINE:
            raise InvalidStateTransition(
                entity_type="Bot",
                current_state=self.status.value,
                attempted_action="go_busy",
            )
        self.status = BotStatus.BUSY
        self.updated_at = datetime.now(timezone.utc)

    def go_offline(self) -> None:
        """
        Transition bot to offline status.

        Valid from: any state
        """
        self.status = BotStatus.OFFLINE
        self.updated_at = datetime.now(timezone.utc)

    def heartbeat(self) -> None:
        """
        Update last_seen timestamp and ensure bot is online.

        If bot is offline, automatically transitions to online.
        Maintains busy status if currently busy.
        """
        if self.status == BotStatus.OFFLINE:
            self.status = BotStatus.ONLINE

        self.last_seen = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def has_capability(self, capability: str) -> bool:
        """
        Check if bot has a specific capability.

        Args:
            capability: Capability name (case-sensitive)

        Returns:
            True if bot has the capability, False otherwise
        """
        return capability in self.capabilities

    def is_available(self) -> bool:
        """
        Check if bot is available for new tasks.

        Returns:
            True if status is ONLINE, False otherwise
        """
        return self.status == BotStatus.ONLINE

    def is_stale(self, timeout_seconds: int = 90) -> bool:
        """
        Check if bot hasn't sent heartbeat recently.

        Args:
            timeout_seconds: Maximum seconds since last heartbeat

        Returns:
            True if bot is stale (no recent heartbeat), False otherwise
        """
        if self.last_seen is None:
            return True

        now = datetime.now(timezone.utc)
        elapsed = (now - self.last_seen).total_seconds()
        return elapsed > timeout_seconds

    model_config = ConfigDict(
        use_enum_values=False,  # Keep enum objects, don't convert to strings
        validate_assignment=True,  # Validate on field assignment
    )
