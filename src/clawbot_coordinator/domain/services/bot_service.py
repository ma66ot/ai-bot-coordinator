"""
Bot service - business logic for bot management.

This service coordinates bot registration, heartbeat tracking, and availability management.
Accepts repository interface for dependency injection (see CLAUDE.md Checkpoint 3).
"""
from typing import Any
from uuid import UUID

from ..models.bot import Bot
from ..repositories.bot_repo import BotRepository
from ...exceptions import ResourceNotFound


class BotService:
    """
    Service layer for bot management.

    Orchestrates business logic for bot operations using dependency injection.
    """

    def __init__(self, repository: BotRepository) -> None:
        """
        Initialize service with repository dependency.

        Args:
            repository: BotRepository interface (can be any implementation)
        """
        self._repo = repository

    async def register_bot(
        self,
        name: str,
        capabilities: list[str],
        metadata: dict[str, Any] | None = None,
    ) -> Bot:
        """
        Register a new bot in the system.

        Creates a new bot with offline status. Bot must send heartbeat to go online.

        Args:
            name: Bot name/identifier
            capabilities: List of capabilities the bot supports
            metadata: Optional metadata dictionary

        Returns:
            Newly created Bot instance
        """
        bot = Bot(
            name=name,
            capabilities=capabilities,
            metadata=metadata or {},
        )

        await self._repo.save(bot)
        return bot

    async def heartbeat(self, bot_id: UUID) -> None:
        """
        Process heartbeat from a bot.

        Updates last_seen timestamp and sets bot to online if offline.
        Raises ResourceNotFound if bot doesn't exist.

        Args:
            bot_id: ID of the bot sending heartbeat

        Raises:
            ResourceNotFound: If bot with given ID doesn't exist
        """
        bot = await self._repo.get(bot_id)
        if not bot:
            raise ResourceNotFound("Bot", str(bot_id))

        bot.heartbeat()
        await self._repo.save(bot)

    async def get_bot(self, bot_id: UUID) -> Bot:
        """
        Fetch bot by ID.

        Args:
            bot_id: ID of the bot to fetch

        Returns:
            Bot instance

        Raises:
            ResourceNotFound: If bot doesn't exist
        """
        bot = await self._repo.get(bot_id)
        if not bot:
            raise ResourceNotFound("Bot", str(bot_id))
        return bot

    async def get_by_capability(self, capability: str) -> list[Bot]:
        """
        Find all bots that have a specific capability.

        Args:
            capability: Capability name to search for

        Returns:
            List of bots with the capability (may be empty)
        """
        return await self._repo.get_by_capability(capability)

    async def get_available_bots(self, capability: str | None = None) -> list[Bot]:
        """
        Get all available (online) bots.

        Args:
            capability: Optional capability filter

        Returns:
            List of online bots, optionally filtered by capability
        """
        return await self._repo.get_available_bots(capability)

    async def mark_bot_busy(self, bot_id: UUID) -> None:
        """
        Mark a bot as busy (working on a task).

        Args:
            bot_id: ID of the bot to mark busy

        Raises:
            ResourceNotFound: If bot doesn't exist
            InvalidStateTransition: If bot is not online
        """
        bot = await self._repo.get(bot_id)
        if not bot:
            raise ResourceNotFound("Bot", str(bot_id))

        bot.go_busy()
        await self._repo.save(bot)

    async def mark_bot_available(self, bot_id: UUID) -> None:
        """
        Mark a bot as available (online and ready for work).

        Args:
            bot_id: ID of the bot to mark available

        Raises:
            ResourceNotFound: If bot doesn't exist
        """
        bot = await self._repo.get(bot_id)
        if not bot:
            raise ResourceNotFound("Bot", str(bot_id))

        bot.go_online()
        await self._repo.save(bot)

    async def list_bots(self, skip: int = 0, limit: int = 100) -> list[Bot]:
        """
        List all bots with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of bots
        """
        return await self._repo.get_all(skip=skip, limit=limit)

    async def save_bot(self, bot: Bot) -> None:
        """
        Save bot changes to repository.

        Useful for updating bot state after domain model changes.

        Args:
            bot: Bot instance to save
        """
        await self._repo.save(bot)

    async def delete_bot(self, bot_id: UUID) -> None:
        """
        Delete a bot from the system.

        Args:
            bot_id: ID of the bot to delete

        Raises:
            ResourceNotFound: If bot doesn't exist
        """
        deleted = await self._repo.delete(bot_id)
        if not deleted:
            raise ResourceNotFound("Bot", str(bot_id))
