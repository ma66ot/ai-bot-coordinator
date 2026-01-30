"""
Bot repository interface (Port).

This is an abstract interface that defines how the domain layer
interacts with persistence. Infrastructure layer provides concrete implementations.

See CLAUDE.md Protocol 3 for layer isolation rules.
"""
from abc import ABC, abstractmethod
from uuid import UUID

from ..models.bot import Bot


class BotRepository(ABC):
    """Abstract repository for Bot persistence operations."""

    @abstractmethod
    async def get(self, bot_id: UUID) -> Bot | None:
        """
        Fetch bot by ID.

        Args:
            bot_id: Unique identifier of the bot

        Returns:
            Bot if found, None otherwise
        """
        pass

    @abstractmethod
    async def save(self, bot: Bot) -> None:
        """
        Persist a bot (insert or update).

        Must handle both new bots and updates to existing bots.

        Args:
            bot: Bot domain model to persist
        """
        pass

    @abstractmethod
    async def delete(self, bot_id: UUID) -> bool:
        """
        Delete a bot by ID.

        Args:
            bot_id: Unique identifier of the bot

        Returns:
            True if bot was deleted, False if not found
        """
        pass

    @abstractmethod
    async def get_all(self, skip: int = 0, limit: int = 100) -> list[Bot]:
        """
        Fetch all bots with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Bot domain models
        """
        pass

    @abstractmethod
    async def get_by_capability(self, capability: str) -> list[Bot]:
        """
        Find all bots that have a specific capability.

        Args:
            capability: Capability name to search for

        Returns:
            List of bots with the specified capability
        """
        pass

    @abstractmethod
    async def get_by_status(self, status: str) -> list[Bot]:
        """
        Find all bots with a specific status.

        Args:
            status: Bot status ("online", "offline", "busy")

        Returns:
            List of bots with the specified status
        """
        pass

    @abstractmethod
    async def get_available_bots(self, capability: str | None = None) -> list[Bot]:
        """
        Find all available (online) bots, optionally filtered by capability.

        Args:
            capability: Optional capability filter

        Returns:
            List of available bots
        """
        pass
