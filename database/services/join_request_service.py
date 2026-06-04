import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Channel, ChannelJoin

logger = logging.getLogger(__name__)


class JoinRequestService:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC).replace(tzinfo=None)

    async def _save(self, obj):
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def _upsert_join(
        self,
        user_id: int,
        channel_id: int,
        is_joined: bool,
    ) -> ChannelJoin | None:
        try:
            join = await self.get_channel_join(
                user_id=user_id,
                channel_id=channel_id,
            )

            if join:
                join.is_joined = is_joined
                join.left_at = None

                return await self._save(join)

            join = ChannelJoin(
                user_id=user_id,
                channel_id=channel_id,
                is_joined=is_joined,
                left_at=None,
            )

            return await self._save(join)

        except SQLAlchemyError as e:
            await self.session.rollback()

            logger.error(
                f"ChannelJoin saqlashda xatolik "
                f"(user={user_id}, channel={channel_id}): {e}"
            )

            return None

    async def get_channel_join(
        self,
        user_id: int,
        channel_id: int,
    ) -> ChannelJoin | None:
        try:
            result = await self.session.execute(
                select(ChannelJoin).where(
                    ChannelJoin.user_id == user_id,
                    ChannelJoin.channel_id == channel_id,
                )
            )

            return result.scalar_one_or_none()

        except SQLAlchemyError as e:
            logger.error(
                f"ChannelJoin olishda xatolik "
                f"(user={user_id}, channel={channel_id}): {e}"
            )

            return None

    async def get_active_channel_join(
        self,
        user_id: int,
        channel_id: int,
    ) -> ChannelJoin | None:
        try:
            result = await self.session.execute(
                select(ChannelJoin).where(
                    ChannelJoin.user_id == user_id,
                    ChannelJoin.channel_id == channel_id,
                    ChannelJoin.is_joined.is_(True),
                )
            )

            return result.scalar_one_or_none()

        except SQLAlchemyError as e:
            logger.error(
                f"Faol ChannelJoin olishda xatolik "
                f"(user={user_id}, channel={channel_id}): {e}"
            )

            return None

    async def get_channel_by_telegram_chat_id(
        self,
        telegram_chat_id: int,
    ) -> Channel | None:
        try:
            result = await self.session.execute(
                select(Channel).where(Channel.telegram_chat_id == telegram_chat_id)
            )

            return result.scalar_one_or_none()

        except SQLAlchemyError as e:
            logger.error(f"Channel olishda xatolik (chat_id={telegram_chat_id}): {e}")

            return None

    async def mark_channel_join_requested(
        self,
        user_id: int,
        channel_id: int,
    ) -> ChannelJoin | None:
        return await self._upsert_join(
            user_id=user_id,
            channel_id=channel_id,
            is_joined=False,
        )

    async def mark_channel_joined(
        self,
        user_id: int,
        channel_id: int,
    ) -> ChannelJoin | None:
        return await self._upsert_join(
            user_id=user_id,
            channel_id=channel_id,
            is_joined=True,
        )

    async def mark_channel_joined_by_chat_id(
        self,
        user_id: int,
        telegram_chat_id: int,
    ) -> ChannelJoin | None:
        channel = await self.get_channel_by_telegram_chat_id(telegram_chat_id)

        if not channel:
            return None

        return await self.mark_channel_joined(
            user_id=user_id,
            channel_id=channel.channel_id,
        )

    async def mark_channel_request_by_chat_id(
        self,
        user_id: int,
        telegram_chat_id: int,
    ) -> ChannelJoin | None:
        channel = await self.get_channel_by_telegram_chat_id(telegram_chat_id)

        if not channel:
            return None

        return await self.mark_channel_join_requested(
            user_id=user_id,
            channel_id=channel.channel_id,
        )

    async def leave_channel_join(
        self,
        user_id: int,
        channel_id: int,
    ) -> bool:
        try:
            join = await self.get_active_channel_join(
                user_id=user_id,
                channel_id=channel_id,
            )

            if not join:
                return False

            join.is_joined = False
            join.left_at = self._now()

            await self.session.commit()

            return True

        except SQLAlchemyError as e:
            await self.session.rollback()

            logger.error(
                f"Kanaldan chiqishni saqlashda xatolik "
                f"(user={user_id}, channel={channel_id}): {e}"
            )

            return False
