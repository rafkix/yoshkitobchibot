import logging
from datetime import datetime, UTC
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Channel, ChannelJoin

logger = logging.getLogger(__name__)


class JoinRequestService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_channel_join(
        self, user_id: int, channel_id: int
    ) -> ChannelJoin | None:
        """Foydalanuvchining kanalga ulanish yozuvini olish."""
        try:
            result = await self.session.execute(
                select(ChannelJoin).where(
                    ChannelJoin.user_id == user_id,
                    ChannelJoin.channel_id == channel_id,
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(
                f"❌ ChannelJoin yozuvini olishda xatolik (user={user_id}, channel={channel_id}): {e}"
            )
            return None

    async def get_active_channel_join(
        self, user_id: int, channel_id: int
    ) -> ChannelJoin | None:
        """Foydalanuvchi kanalga haqiqatan qo‘shilganligini tekshirish."""
        try:
            result = await self.session.execute(
                select(ChannelJoin).where(
                    ChannelJoin.user_id == user_id,
                    ChannelJoin.channel_id == channel_id,
                    ChannelJoin.is_joined.is_(True),
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(
                f"❌ Faol ChannelJoin yozuvini olishda xatolik (user={user_id}, channel={channel_id}): {e}"
            )
            return None

    async def get_channel_by_telegram_chat_id(
        self, telegram_chat_id: int
    ) -> Channel | None:
        """Telegram chat ID orqali kanalni topish."""
        try:
            result = await self.session.execute(
                select(Channel).where(Channel.telegram_chat_id == telegram_chat_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(
                f"❌ Telegram chat ID bo‘yicha kanalni olishda xatolik (chat_id={telegram_chat_id}): {e}"
            )
            return None

    async def mark_channel_join_requested(
        self, user_id: int, channel_id: int
    ) -> ChannelJoin | None:
        """Foydalanuvchining kanal so‘rovini qayd etish (admin tasdiqiga qadar kutish holati)."""
        try:
            existing_join = await self.get_channel_join(user_id, channel_id)
            if existing_join:
                existing_join.is_joined = False
                existing_join.left_at = None
                await self.session.commit()
                await self.session.refresh(existing_join)
                return existing_join

            new_join = ChannelJoin(
                user_id=user_id, channel_id=channel_id, is_joined=False, left_at=None
            )
            self.session.add(new_join)
            await self.session.commit()
            await self.session.refresh(new_join)
            return new_join
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(
                f"❌ Kanal so‘rovini saqlashda xatolik (user={user_id}, channel={channel_id}): {e}"
            )
            return None

    async def mark_channel_joined(
        self, user_id: int, channel_id: int
    ) -> ChannelJoin | None:
        """Foydalanuvchi kanalga qo‘shilganini tasdiqlash."""
        try:
            existing_join = await self.get_channel_join(user_id, channel_id)
            if existing_join:
                existing_join.is_joined = True
                existing_join.left_at = None
                await self.session.commit()
                await self.session.refresh(existing_join)
                return existing_join

            new_join = ChannelJoin(
                user_id=user_id, channel_id=channel_id, is_joined=True, left_at=None
            )
            self.session.add(new_join)
            await self.session.commit()
            await self.session.refresh(new_join)
            return new_join
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(
                f"❌ Kanalga qo‘shilishni saqlashda xatolik (user={user_id}, channel={channel_id}): {e}"
            )
            return None

    async def mark_channel_joined_by_chat_id(
        self, user_id: int, telegram_chat_id: int
    ) -> ChannelJoin | None:
        """Telegram chat ID orqali foydalanuvchini kanalga qo‘shilgan deb belgilash."""
        channel = await self.get_channel_by_telegram_chat_id(telegram_chat_id)
        if not channel:
            return None
        return await self.mark_channel_joined(
            user_id=user_id, channel_id=channel.channel_id
        )

    async def mark_channel_request_by_chat_id(
        self, user_id: int, telegram_chat_id: int
    ) -> ChannelJoin | None:
        """Telegram chat ID orqali kanal so‘rovini kutish holatiga o‘tkazish."""
        channel = await self.get_channel_by_telegram_chat_id(telegram_chat_id)
        if not channel:
            return None
        return await self.mark_channel_join_requested(
            user_id=user_id, channel_id=channel.channel_id
        )

    async def leave_channel_join(self, user_id: int, channel_id: int) -> bool:
        """Foydalanuvchi kanaldan chiqqanini qayd etish."""
        try:
            join = await self.get_channel_join(user_id, channel_id)
            if not join or not join.is_joined:
                return False
            join.is_joined = False
            join.left_at = datetime.now(UTC).replace(tzinfo=None)
            await self.session.commit()
            return True
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(
                f"❌ Kanaldan chiqishni saqlashda xatolik (user={user_id}, channel={channel_id}): {e}"
            )
            return False
