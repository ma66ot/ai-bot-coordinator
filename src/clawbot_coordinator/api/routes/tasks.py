"""
Task API routes.

HTTP endpoints for task management operations.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ...dependencies import get_task_service
from ...domain.services.task_service import TaskService
from ...exceptions import DomainError, InvalidStateTransition, ResourceNotFound
from ..schemas.task_schemas import (
    TaskAssign,
    TaskCreate,
    TaskList,
    TaskResponse,
    TaskResult,
    TaskStatusUpdate,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task",
    description="Create a new task in pending state for a workflow.",
)
async def create_task(
    payload: TaskCreate,
    service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    """Create a new task."""
    try:
        task = await service.create_task(
            workflow_id=payload.workflow_id,
            payload=payload.payload,
            timeout_seconds=payload.timeout_seconds,
        )
        return TaskResponse.from_domain(task)
    except DomainError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "",
    response_model=TaskList,
    summary="List all tasks",
    description="Get paginated list of all tasks.",
)
async def list_tasks(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    service: TaskService = Depends(get_task_service),
) -> TaskList:
    """List all tasks with pagination."""
    tasks = await service.list_tasks(skip=skip, limit=limit)
    return TaskList.from_domain_list(tasks, total=len(tasks), skip=skip, limit=limit)


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Get task by ID",
    description="Retrieve details of a specific task.",
)
async def get_task(
    task_id: UUID,
    service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    """Get task by ID."""
    try:
        task = await service.get_task(task_id)
        return TaskResponse.from_domain(task)
    except ResourceNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/{task_id}/assign",
    response_model=TaskStatusUpdate,
    summary="Assign task to bot",
    description="Assign a pending task to a bot.",
)
async def assign_task(
    task_id: UUID,
    payload: TaskAssign,
    service: TaskService = Depends(get_task_service),
) -> TaskStatusUpdate:
    """Assign task to a bot."""
    try:
        await service.assign_task_to_bot(task_id, payload.bot_id)
        task = await service.get_task(task_id)
        return TaskStatusUpdate(
            task_id=task.id,
            status=task.status,
            message="Task assigned to bot",
        )
    except ResourceNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidStateTransition as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/{task_id}/start",
    response_model=TaskStatusUpdate,
    summary="Start task execution",
    description="Transition task from assigned to in-progress.",
)
async def start_task(
    task_id: UUID,
    service: TaskService = Depends(get_task_service),
) -> TaskStatusUpdate:
    """Start task execution."""
    try:
        await service.start_task(task_id)
        task = await service.get_task(task_id)
        return TaskStatusUpdate(
            task_id=task.id,
            status=task.status,
            message="Task started",
        )
    except ResourceNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidStateTransition as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/{task_id}/complete",
    response_model=TaskStatusUpdate,
    summary="Complete task",
    description="Mark task as successfully completed with result.",
)
async def complete_task(
    task_id: UUID,
    payload: TaskResult,
    service: TaskService = Depends(get_task_service),
) -> TaskStatusUpdate:
    """Complete a task with result."""
    try:
        await service.complete_task(task_id, payload.result)
        task = await service.get_task(task_id)
        return TaskStatusUpdate(
            task_id=task.id,
            status=task.status,
            message="Task completed successfully",
        )
    except ResourceNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidStateTransition as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/{task_id}/fail",
    response_model=TaskStatusUpdate,
    summary="Fail task",
    description="Mark task as failed with error information.",
)
async def fail_task(
    task_id: UUID,
    payload: TaskResult,
    service: TaskService = Depends(get_task_service),
) -> TaskStatusUpdate:
    """Fail a task with error information."""
    try:
        await service.fail_task(task_id, payload.result)
        task = await service.get_task(task_id)
        return TaskStatusUpdate(
            task_id=task.id,
            status=task.status,
            message="Task marked as failed",
        )
    except ResourceNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidStateTransition as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/{task_id}/cancel",
    response_model=TaskStatusUpdate,
    summary="Cancel task",
    description="Cancel a task (can be done from any state).",
)
async def cancel_task(
    task_id: UUID,
    service: TaskService = Depends(get_task_service),
) -> TaskStatusUpdate:
    """Cancel a task."""
    try:
        await service.cancel_task(task_id)
        task = await service.get_task(task_id)
        return TaskStatusUpdate(
            task_id=task.id,
            status=task.status,
            message="Task cancelled",
        )
    except ResourceNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/workflow/{workflow_id}",
    response_model=list[TaskResponse],
    summary="Get tasks by workflow",
    description="Get all tasks belonging to a specific workflow.",
)
async def get_tasks_by_workflow(
    workflow_id: UUID,
    service: TaskService = Depends(get_task_service),
) -> list[TaskResponse]:
    """Get all tasks for a workflow."""
    tasks = await service.get_tasks_by_workflow(workflow_id)
    return [TaskResponse.from_domain(task) for task in tasks]


@router.get(
    "/bot/{bot_id}",
    response_model=list[TaskResponse],
    summary="Get tasks by bot",
    description="Get all tasks assigned to a specific bot.",
)
async def get_tasks_by_bot(
    bot_id: UUID,
    service: TaskService = Depends(get_task_service),
) -> list[TaskResponse]:
    """Get all tasks assigned to a bot."""
    tasks = await service.get_tasks_by_bot(bot_id)
    return [TaskResponse.from_domain(task) for task in tasks]


@router.get(
    "/status/pending",
    response_model=list[TaskResponse],
    summary="Get pending tasks",
    description="Get pending tasks ready for assignment.",
)
async def get_pending_tasks(
    limit: int = Query(10, ge=1, le=100, description="Maximum tasks to return"),
    service: TaskService = Depends(get_task_service),
) -> list[TaskResponse]:
    """Get pending tasks."""
    tasks = await service.get_pending_tasks(limit)
    return [TaskResponse.from_domain(task) for task in tasks]


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete task",
    description="Remove a task from the system.",
)
async def delete_task(
    task_id: UUID,
    service: TaskService = Depends(get_task_service),
) -> None:
    """Delete a task."""
    try:
        await service.delete_task(task_id)
    except ResourceNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
