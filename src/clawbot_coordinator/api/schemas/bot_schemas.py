"""
API schemas (DTOs) for Bot endpoints.

These Pydantic models define the API contract for requests and responses.
Separate from domain models to allow API evolution without domain changes.
"""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from ...domain.models.bot import Bot, BotStatus


class BotCreate(BaseModel):
    """Request schema for creating a new bot."""

    name: str = Field(..., min_length=1, max_length=255, description="Bot name/identifier")
    capabilities: list[str] = Field(
        ...,
        min_length=1,
        description="List of capabilities the bot supports",
        examples=[["python", "docker", "kubernetes"]],
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata for the bot",
    )


class BotUpdate(BaseModel):
    """Request schema for updating bot metadata (partial update)."""

    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Updated metadata",
    )


class BotResponse(BaseModel):
    """Response schema for bot data."""

    id: UUID
    name: str
    capabilities: list[str]
    status: BotStatus
    last_seen: datetime | None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, bot: Bot) -> "BotResponse":
        """
        Convert domain model to API response.

        Args:
            bot: Bot domain model

        Returns:
            BotResponse DTO
        """
        return cls(
            id=bot.id,
            name=bot.name,
            capabilities=bot.capabilities,
            status=bot.status,
            last_seen=bot.last_seen,
            metadata=bot.metadata,
            created_at=bot.created_at,
            updated_at=bot.updated_at,
        )

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "worker-bot-001",
                "capabilities": ["python", "docker"],
                "status": "online",
                "last_seen": "2024-01-30T12:00:00Z",
                "metadata": {"version": "1.0", "region": "us-west"},
                "created_at": "2024-01-30T10:00:00Z",
                "updated_at": "2024-01-30T12:00:00Z",
            }
        }
    }


class BotList(BaseModel):
    """Response schema for paginated bot list."""

    items: list[BotResponse]
    total: int
    skip: int
    limit: int

    @classmethod
    def from_domain_list(
        cls, bots: list[Bot], total: int, skip: int, limit: int
    ) -> "BotList":
        """
        Convert list of domain models to paginated response.

        Args:
            bots: List of Bot domain models
            total: Total count of bots (for pagination)
            skip: Number of items skipped
            limit: Maximum items per page

        Returns:
            BotList DTO
        """
        return cls(
            items=[BotResponse.from_domain(bot) for bot in bots],
            total=total,
            skip=skip,
            limit=limit,
        )


class HeartbeatResponse(BaseModel):
    """Response schema for heartbeat acknowledgment."""

    bot_id: UUID
    status: BotStatus
    last_seen: datetime
    message: str = "Heartbeat acknowledged"
