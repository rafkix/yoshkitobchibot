import logging

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Channel

logger = logging.getLogger(__name__)


class ChannelService:
    ALLOWED_UPDATE_FIELDS = {
        "title",
        "telegram_chat_id",
        "channel_link",
        "link_type",
        "is_private",
        "requires_check",
        "previous_subscribers_count",
        "current_subscribers_count",
        "is_active",
    }

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _save(self, obj):
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

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
        try:
            if requires_check is None:
                requires_check = link_type != "external_link"

            channel = Channel(
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

            return await self._save(channel)

        except IntegrityError:
            await self.session.rollback()

            logger.warning(
                "Channel allaqachon mavjud "
                f"(chat_id={telegram_chat_id}, "
                f"link={channel_link})"
            )

            return None

        except SQLAlchemyError as e:
            await self.session.rollback()

            logger.exception(f"Channel yaratishda xatolik: {e}")

            return None

    async def get_channel_by_id(
        self,
        channel_id: int,
    ) -> Channel | None:
        try:
            result = await self.session.execute(
                select(Channel).where(Channel.channel_id == channel_id)
            )

            return result.scalar_one_or_none()

        except SQLAlchemyError as e:
            logger.error(f"Channel olishda xatolik: {e}")

            return None

    async def get_channel_by_chat_id(
        self,
        telegram_chat_id: int,
    ) -> Channel | None:
        try:
            result = await self.session.execute(
                select(Channel).where(Channel.telegram_chat_id == telegram_chat_id)
            )

            return result.scalar_one_or_none()

        except SQLAlchemyError as e:
            logger.error(f"Chat ID bo‘yicha channel olishda xatolik: {e}")

            return None

    async def get_channel_by_link(
        self,
        channel_link: str,
    ) -> Channel | None:
        try:
            result = await self.session.execute(
                select(Channel).where(Channel.channel_link == channel_link)
            )

            return result.scalar_one_or_none()

        except SQLAlchemyError as e:
            logger.error(f"Link bo‘yicha channel olishda xatolik: {e}")

            return None

    async def get_all_channels(
        self,
        active_only: bool = False,
    ) -> list[Channel]:
        try:
            stmt = select(Channel).order_by(Channel.created_at.desc())

            if active_only:
                stmt = stmt.where(Channel.is_active.is_(True))

            result = await self.session.execute(stmt)

            return list(result.scalars().all())

        except SQLAlchemyError as e:
            logger.error(f"Channel ro‘yxatini olishda xatolik: {e}")

            return []

    async def get_channels_by_type(
        self,
        link_type: str,
        active_only: bool = False,
    ) -> list[Channel]:
        try:
            stmt = (
                select(Channel)
                .where(Channel.link_type == link_type)
                .order_by(Channel.created_at.desc())
            )

            if active_only:
                stmt = stmt.where(Channel.is_active.is_(True))

            result = await self.session.execute(stmt)

            return list(result.scalars().all())

        except SQLAlchemyError as e:
            logger.error(f"Channel type bo‘yicha olishda xatolik: {e}")

            return []

    async def get_required_channels(
        self,
    ) -> list[Channel]:
        try:
            result = await self.session.execute(
                select(Channel).where(
                    Channel.is_active.is_(True),
                    Channel.requires_check.is_(True),
                )
            )

            return list(result.scalars().all())

        except SQLAlchemyError as e:
            logger.error(f"Majburiy kanallarni olishda xatolik: {e}")

            return []

    async def get_private_channels(
        self,
    ) -> list[Channel]:
        try:
            result = await self.session.execute(
                select(Channel).where(Channel.is_private.is_(True))
            )

            return list(result.scalars().all())

        except SQLAlchemyError as e:
            logger.error(f"Private kanallarni olishda xatolik: {e}")

            return []

    async def get_public_channels(
        self,
    ) -> list[Channel]:
        try:
            result = await self.session.execute(
                select(Channel).where(Channel.is_private.is_(False))
            )

            return list(result.scalars().all())

        except SQLAlchemyError as e:
            logger.error(f"Public kanallarni olishda xatolik: {e}")

            return []

    async def update_channel(
        self,
        channel_id: int,
        **kwargs,
    ) -> Channel | None:
        try:
            channel = await self.get_channel_by_id(channel_id)

            if not channel:
                return None

            for key, value in kwargs.items():
                if key in self.ALLOWED_UPDATE_FIELDS and value is not None:
                    setattr(channel, key, value)

            return await self._save(channel)

        except IntegrityError:
            await self.session.rollback()

            logger.warning(f"Duplicate qiymat channel update (channel_id={channel_id})")

            return None

        except SQLAlchemyError as e:
            await self.session.rollback()

            logger.exception(f"Channel update xatoligi: {e}")

            return None

    async def update_channel_subscribers(
        self,
        channel_id: int,
        new_count: int,
    ) -> Channel | None:
        channel = await self.get_channel_by_id(channel_id)

        if not channel:
            return None

        return await self.update_channel(
            channel_id,
            previous_subscribers_count=(channel.current_subscribers_count),
            current_subscribers_count=new_count,
        )

    async def activate_channel(
        self,
        channel_id: int,
    ) -> Channel | None:
        return await self.update_channel(
            channel_id,
            is_active=True,
        )

    async def deactivate_channel(
        self,
        channel_id: int,
    ) -> Channel | None:
        return await self.update_channel(
            channel_id,
            is_active=False,
        )

    async def archive_channel(
        self,
        channel_id: int,
    ) -> bool:
        channel = await self.deactivate_channel(channel_id)

        return channel is not None

    async def delete_channel(
        self,
        channel_id: int,
    ) -> bool:
        try:
            channel = await self.get_channel_by_id(channel_id)

            if not channel:
                return False

            await self.session.delete(channel)
            await self.session.commit()

            return True

        except SQLAlchemyError as e:
            await self.session.rollback()

            logger.exception(f"Channel o‘chirishda xatolik: {e}")

            return False

    async def count_channels(
        self,
        active_only: bool = False,
    ) -> int:
        try:
            stmt = select(func.count(Channel.channel_id))

            if active_only:
                stmt = stmt.where(Channel.is_active.is_(True))

            result = await self.session.execute(stmt)

            return int(result.scalar_one() or 0)

        except SQLAlchemyError as e:
            logger.error(f"Channel sonini olishda xatolik: {e}")

            return 0

    async def get_channel_stats(
        self,
    ) -> dict:
        try:
            total = await self.count_channels()

            active = await self.count_channels(active_only=True)

            result = await self.session.execute(
                select(func.count(Channel.channel_id)).where(
                    Channel.is_private.is_(True)
                )
            )

            private_count = int(result.scalar_one() or 0)

            return {
                "total": total,
                "active": active,
                "inactive": total - active,
                "private": private_count,
                "public": total - private_count,
            }

        except SQLAlchemyError as e:
            logger.error(f"Channel statistikasini olishda xatolik: {e}")

            return {}
