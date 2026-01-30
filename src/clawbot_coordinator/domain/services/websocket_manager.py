"""
WebSocket connection manager service.

Manages active WebSocket connections for bots.
Pure domain service with no FastAPI dependencies.
"""
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ConnectionInfo(BaseModel):
    """Information about a bot's WebSocket connection."""

    bot_id: UUID = Field(..., description="Bot ID")
    connected_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When bot connected",
    )


class WebSocketConnectionManager:
    """
    Manages WebSocket connections for bots.

    This is a domain service that tracks active connections.
    The actual WebSocket objects are stored but treated as opaque types.
    """

    def __init__(self) -> None:
        """Initialize connection manager."""
        # Map bot_id -> WebSocket connection
        self._connections: dict[UUID, Any] = {}
        # Map bot_id -> ConnectionInfo
        self._connection_info: dict[UUID, ConnectionInfo] = {}

    def connect(self, bot_id: UUID, websocket: Any) -> None:
        """
        Register a new bot connection.

        If bot already has connection, replaces it (handles reconnection).

        Args:
            bot_id: Bot identifier
            websocket: WebSocket connection object
        """
        self._connections[bot_id] = websocket
        self._connection_info[bot_id] = ConnectionInfo(bot_id=bot_id)

    def disconnect(self, bot_id: UUID) -> None:
        """
        Disconnect a bot.

        Removes connection and info. Safe to call even if bot not connected.

        Args:
            bot_id: Bot identifier
        """
        self._connections.pop(bot_id, None)
        self._connection_info.pop(bot_id, None)

    def is_connected(self, bot_id: UUID) -> bool:
        """
        Check if bot is currently connected.

        Args:
            bot_id: Bot identifier

        Returns:
            True if bot has active connection
        """
        return bot_id in self._connections

    def get_connection(self, bot_id: UUID) -> Any | None:
        """
        Get WebSocket connection for bot.

        Args:
            bot_id: Bot identifier

        Returns:
            WebSocket connection or None if not connected
        """
        return self._connections.get(bot_id)

    def get_connection_info(self, bot_id: UUID) -> ConnectionInfo | None:
        """
        Get connection info for bot.

        Args:
            bot_id: Bot identifier

        Returns:
            ConnectionInfo or None if not connected
        """
        return self._connection_info.get(bot_id)

    def get_connection_count(self) -> int:
        """
        Get total number of active connections.

        Returns:
            Number of connected bots
        """
        return len(self._connections)

    def get_all_connected_bot_ids(self) -> list[UUID]:
        """
        Get list of all connected bot IDs.

        Returns:
            List of bot UUIDs with active connections
        """
        return list(self._connections.keys())
