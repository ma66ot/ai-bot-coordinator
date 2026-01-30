"""WebSocket routes for real-time bot communication."""
import json
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from fastapi.responses import JSONResponse

from ...dependencies import get_bot_service, get_task_service, get_websocket_manager
from ...domain.models.websocket_message import (
    ConnectedMessage,
    HeartbeatMessage,
    MessageType,
    TaskAssignedMessage,
    TaskCompleteMessage,
)
from ...domain.services.bot_service import BotService
from ...domain.services.task_service import TaskService
from ...domain.services.websocket_manager import WebSocketConnectionManager
from ...exceptions import DomainError, ResourceNotFound

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/control")
async def websocket_control(
    websocket: WebSocket,
    bot_id: str,
    ws_manager: WebSocketConnectionManager = Depends(get_websocket_manager),
    bot_service: BotService = Depends(get_bot_service),
    task_service: TaskService = Depends(get_task_service),
) -> None:
    """
    WebSocket endpoint for bot control.

    Bot connects, receives tasks, sends completions, sends heartbeats.

    Query params:
        bot_id: Bot UUID as string

    Protocol:
        - Bot connects with bot_id
        - Server sends connected message
        - Server can push task_assigned messages
        - Bot sends task_complete messages
        - Bot sends heartbeat messages
    """
    # Parse and validate bot_id
    try:
        bot_uuid = UUID(bot_id)
    except ValueError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid bot_id")
        return

    # Verify bot exists
    try:
        bot = await bot_service.get_bot(bot_uuid)
    except ResourceNotFound:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Bot not found")
        return

    # Accept connection
    await websocket.accept()

    # Register connection
    ws_manager.connect(bot_uuid, websocket)

    # Send connected message
    connected_msg = ConnectedMessage(bot_id=bot_uuid)
    await websocket.send_json(connected_msg.model_dump(mode="json"))

    # Mark bot as online
    try:
        if bot.status.value == "offline":
            bot.go_online()
            await bot_service.save_bot(bot)
    except DomainError:
        pass  # Ignore state transition errors

    try:
        # Listen for messages from bot
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            message_type = message.get("type")

            if message_type == MessageType.TASK_COMPLETE:
                # Handle task completion
                await _handle_task_complete(message, task_service, bot_uuid)

            elif message_type == MessageType.HEARTBEAT:
                # Handle heartbeat
                await _handle_heartbeat(bot_uuid, bot_service)

            else:
                # Unknown message type - ignore
                pass

    except WebSocketDisconnect:
        # Bot disconnected
        ws_manager.disconnect(bot_uuid)

        # Mark bot as offline
        try:
            bot = await bot_service.get_bot(bot_uuid)
            bot.go_offline()
            await bot_service.save_bot(bot)
        except (ResourceNotFound, DomainError):
            pass

    except Exception:
        # Unexpected error - disconnect
        ws_manager.disconnect(bot_uuid)


async def _handle_task_complete(
    message: dict,
    task_service: TaskService,
    bot_id: UUID,
) -> None:
    """Handle task completion message from bot."""
    try:
        task_id = UUID(message["payload"]["task_id"])
        success = message["payload"]["success"]

        if success:
            result = message["payload"].get("result", {})
            await task_service.complete_task(task_id, result)
        else:
            error = message["payload"].get("error", "Unknown error")
            await task_service.fail_task(task_id, error)

    except (KeyError, ValueError, ResourceNotFound, DomainError):
        # Invalid message or task not found - ignore
        pass


async def _handle_heartbeat(bot_id: UUID, bot_service: BotService) -> None:
    """Handle heartbeat message from bot."""
    try:
        await bot_service.heartbeat(bot_id)
    except (ResourceNotFound, DomainError):
        # Bot not found or other error - ignore
        pass


@router.post("/ws/broadcast/task/{task_id}")
async def broadcast_task_assignment(
    task_id: UUID,
    bot_id: UUID,
    ws_manager: WebSocketConnectionManager = Depends(get_websocket_manager),
    task_service: TaskService = Depends(get_task_service),
) -> JSONResponse:
    """
    Broadcast task assignment to connected bot.

    This endpoint is called by the task assignment logic to notify
    a bot that it has a new task.

    Args:
        task_id: Task to broadcast
        bot_id: Bot to notify (via WebSocket)

    Returns:
        JSON response with broadcast status
    """
    # Check if bot is connected
    websocket = ws_manager.get_connection(bot_id)
    if not websocket:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Bot not connected"},
        )

    # Get task details
    try:
        task = await task_service.get_task(task_id)
    except ResourceNotFound:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Task not found"},
        )

    # Create and send task assigned message
    message = TaskAssignedMessage(
        task_id=task.id,
        workflow_id=task.workflow_id,
        task_payload=task.payload,
    )

    try:
        await websocket.send_json(message.model_dump(mode="json"))
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "sent", "bot_id": str(bot_id), "task_id": str(task_id)},
        )
    except Exception:
        # Failed to send - bot may have disconnected
        ws_manager.disconnect(bot_id)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Failed to send message"},
        )


@router.get("/ws/connections")
async def list_active_connections(
    ws_manager: WebSocketConnectionManager = Depends(get_websocket_manager),
) -> JSONResponse:
    """
    List all active WebSocket connections.

    Returns:
        JSON with connection count and bot IDs
    """
    bot_ids = ws_manager.get_all_connected_bot_ids()
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "count": ws_manager.get_connection_count(),
            "bot_ids": [str(bot_id) for bot_id in bot_ids],
        },
    )
