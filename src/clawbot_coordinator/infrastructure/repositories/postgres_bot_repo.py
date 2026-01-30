"""
PostgreSQL implementation of BotRepository.

Maps between Bot domain models and BotORM database models.
All database-specific logic stays in this infrastructure layer.
"""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import BotORM
from ...domain.models.bot import Bot, BotStatus
from ...domain.repositories.bot_repo import BotRepository


class PostgresBotRepository(BotRepository):
    """PostgreSQL implementation of the Bot repository."""

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session

    async def get(self, bot_id: UUID) -> Bot | None:
        """Fetch bot by ID."""
        result = await self._session.execute(
            select(BotORM).where(BotORM.id == bot_id)
        )
        orm_obj = result.scalar_one_or_none()
        return self._to_domain(orm_obj) if orm_obj else None

    async def save(self, bot: Bot) -> None:
        """Persist a bot (insert or update)."""
        # Check if bot exists
        result = await self._session.execute(
            select(BotORM).where(BotORM.id == bot.id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing
            self._update_orm(existing, bot)
        else:
            # Insert new
            orm_obj = self._from_domain(bot)
            self._session.add(orm_obj)

        await self._session.flush()

    async def delete(self, bot_id: UUID) -> bool:
        """Delete a bot by ID."""
        result = await self._session.execute(
            select(BotORM).where(BotORM.id == bot_id)
        )
        orm_obj = result.scalar_one_or_none()

        if orm_obj:
            await self._session.delete(orm_obj)
            await self._session.flush()
            return True
        return False

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[Bot]:
        """Fetch all bots with pagination."""
        result = await self._session.execute(
            select(BotORM)
            .order_by(BotORM.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        orm_objs = result.scalars().all()
        return [self._to_domain(obj) for obj in orm_objs]

    async def get_by_capability(self, capability: str) -> list[Bot]:
        """Find all bots that have a specific capability."""
        # NOTE(ai): Get all bots and filter in Python for SQLite compatibility
        # In production PostgreSQL, could use: BotORM.capabilities.contains([capability])
        result = await self._session.execute(select(BotORM))
        orm_objs = result.scalars().all()
        return [
            self._to_domain(obj)
            for obj in orm_objs
            if capability in obj.capabilities
        ]

    async def get_by_status(self, status: str) -> list[Bot]:
        """Find all bots with a specific status."""
        result = await self._session.execute(
            select(BotORM).where(BotORM.status == status)
        )
        orm_objs = result.scalars().all()
        return [self._to_domain(obj) for obj in orm_objs]

    async def get_available_bots(self, capability: str | None = None) -> list[Bot]:
        """Find all available (online) bots, optionally filtered by capability."""
        query = select(BotORM).where(BotORM.status == BotStatus.ONLINE.value)
        result = await self._session.execute(query)
        orm_objs = result.scalars().all()

        # Filter by capability in Python for SQLite compatibility
        if capability:
            return [
                self._to_domain(obj)
                for obj in orm_objs
                if capability in obj.capabilities
            ]
        return [self._to_domain(obj) for obj in orm_objs]

    @staticmethod
    def _to_domain(orm_obj: BotORM) -> Bot:
        """
        Convert ORM model to domain model.

        Args:
            orm_obj: SQLAlchemy ORM object

        Returns:
            Bot domain model
        """
        return Bot(
            id=orm_obj.id,
            name=orm_obj.name,
            capabilities=orm_obj.capabilities,
            status=BotStatus(orm_obj.status),
            last_seen=orm_obj.last_seen,
            metadata=orm_obj.metadata_,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )

    @staticmethod
    def _from_domain(bot: Bot) -> BotORM:
        """
        Convert domain model to ORM model.

        Args:
            bot: Bot domain model

        Returns:
            BotORM SQLAlchemy object
        """
        return BotORM(
            id=bot.id,
            name=bot.name,
            capabilities=bot.capabilities,
            status=bot.status.value,
            last_seen=bot.last_seen,
            metadata_=bot.metadata,
            created_at=bot.created_at,
            updated_at=bot.updated_at,
        )

    @staticmethod
    def _update_orm(orm_obj: BotORM, bot: Bot) -> None:
        """
        Update ORM object fields from domain model.

        Args:
            orm_obj: Existing SQLAlchemy ORM object to update
            bot: Source Bot domain model
        """
        orm_obj.name = bot.name
        orm_obj.capabilities = bot.capabilities
        orm_obj.status = bot.status.value
        orm_obj.last_seen = bot.last_seen
        orm_obj.metadata_ = bot.metadata
        orm_obj.updated_at = bot.updated_at
