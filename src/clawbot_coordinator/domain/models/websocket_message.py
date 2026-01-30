"""
WebSocket message models.

These are pure domain models for WebSocket communication protocol.
No FastAPI or infrastructure dependencies.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class MessageType(str, Enum):
    """WebSocket message types."""

    CONNECTED = "connected"
    TASK_ASSIGNED = "task_assigned"
    TASK_COMPLETE = "task_complete"
    HEARTBEAT = "heartbeat"


class WebSocketMessage(BaseModel):
    """Base WebSocket message."""

    type: MessageType = Field(..., description="Message type")
    payload: dict[str, Any] = Field(default_factory=dict, description="Message payload")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Message timestamp",
    )


class ConnectedMessage(WebSocketMessage):
    """Message sent when bot successfully connects."""

    bot_id: UUID = Field(..., description="Connected bot ID")
    type: MessageType = Field(default=MessageType.CONNECTED, description="Message type")

    @model_validator(mode="after")
    def populate_payload(self) -> "ConnectedMessage":
        """Populate payload with bot_id."""
        self.payload["bot_id"] = str(self.bot_id)
        return self


class TaskAssignedMessage(WebSocketMessage):
    """Message sent when task is assigned to bot."""

    task_id: UUID = Field(..., description="Assigned task ID")
    workflow_id: UUID = Field(..., description="Workflow ID")
    task_payload: dict[str, Any] = Field(..., description="Task execution payload")
    type: MessageType = Field(default=MessageType.TASK_ASSIGNED, description="Message type")

    @model_validator(mode="after")
    def populate_payload(self) -> "TaskAssignedMessage":
        """Populate payload with task data."""
        self.payload["task_id"] = str(self.task_id)
        self.payload["workflow_id"] = str(self.workflow_id)
        self.payload["task_payload"] = self.task_payload
        return self


class TaskCompleteMessage(WebSocketMessage):
    """Message sent by bot when task is completed."""

    task_id: UUID = Field(..., description="Completed task ID")
    success: bool = Field(..., description="Whether task succeeded")
    result: dict[str, Any] | None = Field(default=None, description="Task result if successful")
    error: str | None = Field(default=None, description="Error message if failed")
    type: MessageType = Field(default=MessageType.TASK_COMPLETE, description="Message type")

    @model_validator(mode="after")
    def populate_payload(self) -> "TaskCompleteMessage":
        """Populate payload with task completion data."""
        self.payload["task_id"] = str(self.task_id)
        self.payload["success"] = self.success
        if self.result is not None:
            self.payload["result"] = self.result
        if self.error is not None:
            self.payload["error"] = self.error
        return self


class HeartbeatMessage(WebSocketMessage):
    """Heartbeat message to keep connection alive."""

    bot_id: UUID = Field(..., description="Bot ID sending heartbeat")
    type: MessageType = Field(default=MessageType.HEARTBEAT, description="Message type")

    @model_validator(mode="after")
    def populate_payload(self) -> "HeartbeatMessage":
        """Populate payload with bot_id."""
        self.payload["bot_id"] = str(self.bot_id)
        return self
