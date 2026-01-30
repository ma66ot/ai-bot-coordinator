"""Workflow API routes."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ...dependencies import get_workflow_service
from ...domain.services.workflow_service import WorkflowService
from ...exceptions import DomainError, ResourceNotFound
from ..schemas.task_schemas import TaskResponse
from ..schemas.workflow_schemas import WorkflowCreate, WorkflowResponse, WorkflowWithTasks

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    payload: WorkflowCreate,
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowResponse:
    """Create a new workflow with tasks."""
    try:
        workflow = await service.create_workflow(
            name=payload.name,
            description=payload.description,
            task_payloads=payload.task_payloads,
            metadata=payload.metadata,
        )
        return WorkflowResponse.from_domain(workflow)
    except DomainError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=list[WorkflowResponse])
async def list_workflows(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: WorkflowService = Depends(get_workflow_service),
) -> list[WorkflowResponse]:
    """List all workflows."""
    workflows = await service.list_workflows(skip=skip, limit=limit)
    return [WorkflowResponse.from_domain(w) for w in workflows]


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: UUID,
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowResponse:
    """Get workflow by ID."""
    try:
        workflow = await service.get_workflow(workflow_id)
        return WorkflowResponse.from_domain(workflow)
    except ResourceNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{workflow_id}/tasks", response_model=WorkflowWithTasks)
async def get_workflow_with_tasks(
    workflow_id: UUID,
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowWithTasks:
    """Get workflow with all its tasks."""
    try:
        workflow, tasks = await service.get_workflow_with_tasks(workflow_id)
        return WorkflowWithTasks(
            workflow=WorkflowResponse.from_domain(workflow),
            tasks=[TaskResponse.from_domain(t) for t in tasks],
        )
    except ResourceNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{workflow_id}/start", response_model=WorkflowResponse)
async def start_workflow(
    workflow_id: UUID,
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowResponse:
    """Start workflow execution."""
    try:
        await service.start_workflow(workflow_id)
        workflow = await service.get_workflow(workflow_id)
        return WorkflowResponse.from_domain(workflow)
    except ResourceNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DomainError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: UUID,
    service: WorkflowService = Depends(get_workflow_service),
) -> None:
    """Delete a workflow."""
    try:
        await service.delete_workflow(workflow_id)
    except ResourceNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
