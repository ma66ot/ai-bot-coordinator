"""Unit tests for WebSocket message models."""
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError as PydanticValidationError

from clawbot_coordinator.domain.models.websocket_message import (
    MessageType,
    WebSocketMessage,
    ConnectedMessage,
    TaskAssignedMessage,
    TaskCompleteMessage,
    HeartbeatMessage,
)


class TestMessageType:
    """Test message type enum."""

    def test_message_types_exist(self) -> None:
        """Should have all required message types."""
        assert MessageType.CONNECTED == "connected"
        assert MessageType.TASK_ASSIGNED == "task_assigned"
        assert MessageType.TASK_COMPLETE == "task_complete"
        assert MessageType.HEARTBEAT == "heartbeat"


class TestWebSocketMessage:
    """Test base WebSocket message."""

    def test_create_message_with_minimal_fields(self) -> None:
        """Should create message with only type."""
        msg = WebSocketMessage(type=MessageType.HEARTBEAT)
        assert msg.type == MessageType.HEARTBEAT
        assert isinstance(msg.timestamp, datetime)
        assert msg.payload == {}

    def test_create_message_with_payload(self) -> None:
        """Should create message with custom payload."""
        payload = {"key": "value", "count": 42}
        msg = WebSocketMessage(type=MessageType.CONNECTED, payload=payload)
        assert msg.payload == payload

    def test_message_requires_type(self) -> None:
        """Should require message type."""
        with pytest.raises(PydanticValidationError):
            WebSocketMessage()  # type: ignore

    def test_message_timestamp_is_timezone_aware(self) -> None:
        """Should have timezone-aware timestamp."""
        msg = WebSocketMessage(type=MessageType.HEARTBEAT)
        assert msg.timestamp.tzinfo is not None


class TestConnectedMessage:
    """Test connected message."""

    def test_create_connected_message(self) -> None:
        """Should create connected message with bot_id."""
        bot_id = uuid4()
        msg = ConnectedMessage(bot_id=bot_id)
        assert msg.type == MessageType.CONNECTED
        assert msg.bot_id == bot_id
        assert msg.payload["bot_id"] == str(bot_id)

    def test_connected_message_requires_bot_id(self) -> None:
        """Should require bot_id."""
        with pytest.raises(PydanticValidationError):
            ConnectedMessage()  # type: ignore


class TestTaskAssignedMessage:
    """Test task assigned message."""

    def test_create_task_assigned_message(self) -> None:
        """Should create task assigned message."""
        task_id = uuid4()
        workflow_id = uuid4()
        payload = {"action": "build", "target": "app"}

        msg = TaskAssignedMessage(
            task_id=task_id,
            workflow_id=workflow_id,
            task_payload=payload,
        )

        assert msg.type == MessageType.TASK_ASSIGNED
        assert msg.task_id == task_id
        assert msg.workflow_id == workflow_id
        assert msg.task_payload == payload
        assert msg.payload["task_id"] == str(task_id)
        assert msg.payload["workflow_id"] == str(workflow_id)
        assert msg.payload["task_payload"] == payload

    def test_task_assigned_requires_all_fields(self) -> None:
        """Should require task_id, workflow_id, and task_payload."""
        with pytest.raises(PydanticValidationError):
            TaskAssignedMessage()  # type: ignore


class TestTaskCompleteMessage:
    """Test task complete message."""

    def test_create_task_complete_success(self) -> None:
        """Should create task complete message with success."""
        task_id = uuid4()
        result = {"output": "success", "artifacts": ["file1.txt"]}

        msg = TaskCompleteMessage(
            task_id=task_id,
            success=True,
            result=result,
        )

        assert msg.type == MessageType.TASK_COMPLETE
        assert msg.task_id == task_id
        assert msg.success is True
        assert msg.result == result
        assert msg.error is None
        assert msg.payload["task_id"] == str(task_id)
        assert msg.payload["success"] is True
        assert msg.payload["result"] == result

    def test_create_task_complete_failure(self) -> None:
        """Should create task complete message with failure."""
        task_id = uuid4()
        error = "Connection timeout"

        msg = TaskCompleteMessage(
            task_id=task_id,
            success=False,
            error=error,
        )

        assert msg.success is False
        assert msg.error == error
        assert msg.result is None

    def test_task_complete_requires_task_id_and_success(self) -> None:
        """Should require task_id and success flag."""
        with pytest.raises(PydanticValidationError):
            TaskCompleteMessage()  # type: ignore


class TestHeartbeatMessage:
    """Test heartbeat message."""

    def test_create_heartbeat_message(self) -> None:
        """Should create heartbeat message."""
        bot_id = uuid4()
        msg = HeartbeatMessage(bot_id=bot_id)

        assert msg.type == MessageType.HEARTBEAT
        assert msg.bot_id == bot_id
        assert msg.payload["bot_id"] == str(bot_id)

    def test_heartbeat_requires_bot_id(self) -> None:
        """Should require bot_id."""
        with pytest.raises(PydanticValidationError):
            HeartbeatMessage()  # type: ignore


class TestMessageSerialization:
    """Test message serialization."""

    def test_message_to_json(self) -> None:
        """Should serialize message to JSON."""
        bot_id = uuid4()
        msg = ConnectedMessage(bot_id=bot_id)

        json_data = msg.model_dump()
        assert json_data["type"] == "connected"
        assert "timestamp" in json_data
        assert json_data["payload"]["bot_id"] == str(bot_id)

    def test_message_from_json(self) -> None:
        """Should deserialize message from JSON."""
        task_id = uuid4()
        data = {
            "task_id": task_id,
            "success": True,
            "result": {"output": "done"},
        }

        msg = TaskCompleteMessage(**data)
        assert msg.task_id == task_id
        assert msg.success is True
