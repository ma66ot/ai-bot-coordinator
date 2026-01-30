"""Unit tests for WebSocket connection manager."""
from uuid import UUID, uuid4

import pytest

from clawbot_coordinator.domain.services.websocket_manager import (
    WebSocketConnectionManager,
    ConnectionInfo,
)


class TestConnectionInfo:
    """Test connection info model."""

    def test_create_connection_info(self) -> None:
        """Should create connection info with bot_id."""
        bot_id = uuid4()
        info = ConnectionInfo(bot_id=bot_id)
        assert info.bot_id == bot_id
        assert info.connected_at is not None


class TestWebSocketConnectionManager:
    """Test WebSocket connection manager."""

    @pytest.fixture
    def manager(self) -> WebSocketConnectionManager:
        """Create connection manager instance."""
        return WebSocketConnectionManager()

    def test_manager_starts_empty(self, manager: WebSocketConnectionManager) -> None:
        """Should start with no connections."""
        assert manager.get_connection_count() == 0
        assert manager.get_all_connected_bot_ids() == []

    def test_register_connection(self, manager: WebSocketConnectionManager) -> None:
        """Should register new bot connection."""
        bot_id = uuid4()
        connection = object()  # Mock WebSocket connection

        manager.connect(bot_id, connection)

        assert manager.is_connected(bot_id)
        assert manager.get_connection_count() == 1
        assert bot_id in manager.get_all_connected_bot_ids()

    def test_disconnect_bot(self, manager: WebSocketConnectionManager) -> None:
        """Should disconnect bot."""
        bot_id = uuid4()
        connection = object()

        manager.connect(bot_id, connection)
        assert manager.is_connected(bot_id)

        manager.disconnect(bot_id)
        assert not manager.is_connected(bot_id)
        assert manager.get_connection_count() == 0

    def test_get_connection(self, manager: WebSocketConnectionManager) -> None:
        """Should retrieve bot connection."""
        bot_id = uuid4()
        connection = object()

        manager.connect(bot_id, connection)
        retrieved = manager.get_connection(bot_id)

        assert retrieved is connection

    def test_get_connection_returns_none_if_not_found(
        self, manager: WebSocketConnectionManager
    ) -> None:
        """Should return None for non-existent connection."""
        bot_id = uuid4()
        assert manager.get_connection(bot_id) is None

    def test_multiple_connections(self, manager: WebSocketConnectionManager) -> None:
        """Should handle multiple bot connections."""
        bot1 = uuid4()
        bot2 = uuid4()
        conn1 = object()
        conn2 = object()

        manager.connect(bot1, conn1)
        manager.connect(bot2, conn2)

        assert manager.get_connection_count() == 2
        assert manager.is_connected(bot1)
        assert manager.is_connected(bot2)
        assert set(manager.get_all_connected_bot_ids()) == {bot1, bot2}

    def test_disconnect_one_of_many(self, manager: WebSocketConnectionManager) -> None:
        """Should disconnect specific bot without affecting others."""
        bot1 = uuid4()
        bot2 = uuid4()
        conn1 = object()
        conn2 = object()

        manager.connect(bot1, conn1)
        manager.connect(bot2, conn2)
        manager.disconnect(bot1)

        assert not manager.is_connected(bot1)
        assert manager.is_connected(bot2)
        assert manager.get_connection_count() == 1

    def test_reconnect_same_bot(self, manager: WebSocketConnectionManager) -> None:
        """Should allow reconnecting same bot (replaces old connection)."""
        bot_id = uuid4()
        old_conn = object()
        new_conn = object()

        manager.connect(bot_id, old_conn)
        manager.connect(bot_id, new_conn)

        assert manager.get_connection_count() == 1
        assert manager.get_connection(bot_id) is new_conn

    def test_get_connection_info(self, manager: WebSocketConnectionManager) -> None:
        """Should retrieve connection info."""
        bot_id = uuid4()
        connection = object()

        manager.connect(bot_id, connection)
        info = manager.get_connection_info(bot_id)

        assert info is not None
        assert info.bot_id == bot_id
        assert info.connected_at is not None

    def test_get_connection_info_returns_none_if_not_found(
        self, manager: WebSocketConnectionManager
    ) -> None:
        """Should return None for non-existent connection info."""
        bot_id = uuid4()
        assert manager.get_connection_info(bot_id) is None

    def test_disconnect_nonexistent_bot_does_not_error(
        self, manager: WebSocketConnectionManager
    ) -> None:
        """Should handle disconnecting non-connected bot gracefully."""
        bot_id = uuid4()
        manager.disconnect(bot_id)  # Should not raise
        assert not manager.is_connected(bot_id)
