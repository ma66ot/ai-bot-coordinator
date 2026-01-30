"""
Bot API routes.

HTTP endpoints for bot management operations.
See CLAUDE.md Protocol 2 - Created after Domain/Infra/Services exist.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ...dependencies import get_bot_service
from ...domain.services.bot_service import BotService
from ...exceptions import DomainError, InvalidStateTransition, ResourceNotFound
from ..schemas.bot_schemas import (
    BotCreate,
    BotList,
    BotResponse,
    HeartbeatResponse,
)

router = APIRouter(prefix="/bots", tags=["bots"])


@router.post(
    "",
    response_model=BotResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new bot",
    description="Create a new bot in the system with specified capabilities.",
)
async def register_bot(
    payload: BotCreate,
    service: BotService = Depends(get_bot_service),
) -> BotResponse:
    """Register a new bot."""
    try:
        bot = await service.register_bot(
            name=payload.name,
            capabilities=payload.capabilities,
            metadata=payload.metadata,
        )
        return BotResponse.from_domain(bot)
    except DomainError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "",
    response_model=BotList,
    summary="List all bots",
    description="Get paginated list of all registered bots.",
)
async def list_bots(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    service: BotService = Depends(get_bot_service),
) -> BotList:
    """List all bots with pagination."""
    bots = await service.list_bots(skip=skip, limit=limit)
    # NOTE: In production, get actual total count from repository
    # For now, returning len(bots) as total
    return BotList.from_domain_list(bots, total=len(bots), skip=skip, limit=limit)


@router.get(
    "/{bot_id}",
    response_model=BotResponse,
    summary="Get bot by ID",
    description="Retrieve details of a specific bot.",
)
async def get_bot(
    bot_id: UUID,
    service: BotService = Depends(get_bot_service),
) -> BotResponse:
    """Get bot by ID."""
    try:
        bot = await service.get_bot(bot_id)
        return BotResponse.from_domain(bot)
    except ResourceNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/{bot_id}/heartbeat",
    response_model=HeartbeatResponse,
    summary="Send bot heartbeat",
    description="Update bot's last_seen timestamp and mark as online if offline.",
)
async def bot_heartbeat(
    bot_id: UUID,
    service: BotService = Depends(get_bot_service),
) -> HeartbeatResponse:
    """Process bot heartbeat."""
    try:
        await service.heartbeat(bot_id)
        bot = await service.get_bot(bot_id)
        return HeartbeatResponse(
            bot_id=bot.id,
            status=bot.status,
            last_seen=bot.last_seen,  # type: ignore
        )
    except ResourceNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DomainError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/{bot_id}/busy",
    response_model=BotResponse,
    summary="Mark bot as busy",
    description="Transition bot to busy status (must be online).",
)
async def mark_bot_busy(
    bot_id: UUID,
    service: BotService = Depends(get_bot_service),
) -> BotResponse:
    """Mark bot as busy."""
    try:
        await service.mark_bot_busy(bot_id)
        bot = await service.get_bot(bot_id)
        return BotResponse.from_domain(bot)
    except ResourceNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidStateTransition as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/{bot_id}/available",
    response_model=BotResponse,
    summary="Mark bot as available",
    description="Transition bot to online status (ready for work).",
)
async def mark_bot_available(
    bot_id: UUID,
    service: BotService = Depends(get_bot_service),
) -> BotResponse:
    """Mark bot as available."""
    try:
        await service.mark_bot_available(bot_id)
        bot = await service.get_bot(bot_id)
        return BotResponse.from_domain(bot)
    except ResourceNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/capability/{capability}",
    response_model=list[BotResponse],
    summary="Find bots by capability",
    description="Get all bots that have a specific capability.",
)
async def get_bots_by_capability(
    capability: str,
    service: BotService = Depends(get_bot_service),
) -> list[BotResponse]:
    """Find bots by capability."""
    bots = await service.get_by_capability(capability)
    return [BotResponse.from_domain(bot) for bot in bots]


@router.get(
    "/available/",
    response_model=list[BotResponse],
    summary="Get available bots",
    description="Get all online bots, optionally filtered by capability.",
)
async def get_available_bots(
    capability: str | None = Query(None, description="Filter by capability"),
    service: BotService = Depends(get_bot_service),
) -> list[BotResponse]:
    """Get available bots."""
    bots = await service.get_available_bots(capability=capability)
    return [BotResponse.from_domain(bot) for bot in bots]


@router.delete(
    "/{bot_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete bot",
    description="Remove a bot from the system.",
)
async def delete_bot(
    bot_id: UUID,
    service: BotService = Depends(get_bot_service),
) -> None:
    """Delete a bot."""
    try:
        await service.delete_bot(bot_id)
    except ResourceNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
