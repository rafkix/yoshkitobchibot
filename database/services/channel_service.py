from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Channel


class ChannelService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_channel(
        self,
        link_type: str,
        title: str | None = None,
        telegram_chat_id: int | None = None,
        channel_link: str | None = None,
        is_private: bool = False,
        requires_check: bool | None = None,
        previous_subscribers_count: int | None = None,
        current_subscribers_count: int | None = None,
        is_active: bool = True,
    ) -> Channel | None:
        """Register a new channel ensuring unique chat constraints."""
        try:
            if telegram_chat_id is not None:
                if await self.get_channel_by_chat_id(telegram_chat_id):
                    return None
            if channel_link is not None:
                if await self.get_channel_by_link(channel_link):
                    return None

            if requires_check is None:
                requires_check = link_type != "external_link"

            new_channel = Channel(
                title=title,
                telegram_chat_id=telegram_chat_id,
                channel_link=channel_link,
                link_type=link_type,
                is_private=is_private,
                requires_check=requires_check,
                previous_subscribers_count=previous_subscribers_count,
                current_subscribers_count=current_subscribers_count,
                is_active=is_active,
            )
            self.session.add(new_channel)
            await self.session.commit()
            await self.session.refresh(new_channel)
            return new_channel
        except SQLAlchemyError as e:
            await self.session.rollback()
            print(f"❌ Error adding channel: {e}")
            return None

    async def get_channel_by_id(self, channel_id: int) -> Channel | None:
        """Retrieve channel by its primary key ID."""
        result = await self.session.execute(
            select(Channel).where(Channel.channel_id == channel_id)
        )
        return result.scalar_one_or_none()

    async def get_channel_by_chat_id(self, telegram_chat_id: int) -> Channel | None:
        """Retrieve channel by its unique Telegram chat identifier."""
        result = await self.session.execute(
            select(Channel).where(Channel.telegram_chat_id == telegram_chat_id)
        )
        return result.scalar_one_or_none()

    async def get_channel_by_link(self, channel_link: str) -> Channel | None:
        """Retrieve channel by its invite link URL."""
        result = await self.session.execute(
            select(Channel).where(Channel.channel_link == channel_link)
        )
        return result.scalar_one_or_none()

    async def get_all_channels(self, active_only: bool = False) -> list[Channel]:
        """Fetch all channels sorted by newest registration entry."""
        stmt = select(Channel).order_by(Channel.created_at.desc())
        if active_only:
            stmt = stmt.where(Channel.is_active.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_channels_by_type(
        self, link_type: str, active_only: bool = False
    ) -> list[Channel]:
        """Fetch channels filtered by link type classification."""
        stmt = (
            select(Channel)
            .where(Channel.link_type == link_type)
            .order_by(Channel.created_at.desc())
        )
        if active_only:
            stmt = stmt.where(Channel.is_active.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_channel(self, channel_id: int, **kwargs) -> Channel | None:
        """Update any attributes of a target channel safely."""
        try:
            channel = await self.get_channel_by_id(channel_id)
            if not channel:
                return None

            for key, value in kwargs.items():
                if value is not None and hasattr(channel, key):
                    setattr(channel, key, value)

            await self.session.commit()
            await self.session.refresh(channel)
            return channel
        except SQLAlchemyError as e:
            await self.session.rollback()
            print(f"❌ Error updating channel: {e}")
            return None

    async def update_channel_subscribers(
        self, channel_id: int, new_count: int
    ) -> Channel | None:
        """Shift subscriber history metrics and record new count."""
        channel = await self.get_channel_by_id(channel_id)
        if not channel:
            return None
        return await self.update_channel(
            channel_id,
            previous_subscribers_count=channel.current_subscribers_count,
            current_subscribers_count=new_count,
        )

    async def set_channel_active(
        self, channel_id: int, is_active: bool
    ) -> Channel | None:
        """Toggle the operational status of a channel object."""
        return await self.update_channel(channel_id, is_active=is_active)

    async def delete_channel(self, channel_id: int) -> bool:
        """Permanently delete a channel metadata signature."""
        try:
            channel = await self.get_channel_by_id(channel_id)
            if not channel:
                return False
            await self.session.delete(channel)
            await self.session.commit()
            return True
        except SQLAlchemyError as e:
            await self.session.rollback()
            print(f"❌ Error deleting channel: {e}")
            return False

    async def count_channels(self, active_only: bool = False) -> int:
        """Get the numeric capacity of loaded tracking channels."""
        stmt = select(func.count(Channel.channel_id))
        if active_only:
            stmt = stmt.where(Channel.is_active.is_(True))
        result = await self.session.execute(stmt)
        return int(result.scalar_one() or 0)
