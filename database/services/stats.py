import logging
from datetime import datetime, UTC, timedelta
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User

logger = logging.getLogger(__name__)


class StatService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def count_total_users(self) -> int:
        """Tizimda ro‘yxatdan o‘tgan va o‘tmagan barcha foydalanuvchilar soni."""
        try:
            result = await self.session.execute(select(func.count(User.user_id)))
            return int(result.scalar_one() or 0)
        except Exception as e:
            logger.error(f"❌ Jami foydalanuvchilar sonini olishda xatolik: {e}")
            return 0

    async def count_registered_users(self) -> int:
        """Ro‘yxatdan o‘tishni yakunlagan foydalanuvchilar soni."""
        try:
            result = await self.session.execute(
                select(func.count(User.user_id)).where(User.is_registered.is_(True))
            )
            return int(result.scalar_one() or 0)
        except Exception as e:
            logger.error(f"❌ Ro‘yxatdan o‘tganlar sonini olishda xatolik: {e}")
            return 0

    async def count_unregistered_users(self) -> int:
        """Ro‘yxatdan o‘tishni hali yakunlamagan foydalanuvchilar soni."""
        try:
            result = await self.session.execute(
                select(func.count(User.user_id)).where(User.is_registered.is_(False))
            )
            return int(result.scalar_one() or 0)
        except Exception as e:
            logger.error(f"❌ Ro‘yxatdan o‘tmaganlar sonini olishda xatolik: {e}")
            return 0

    async def count_new_users_since(self, days: int) -> int:
        """So‘nggi N kun ichida qo‘shilgan foydalanuvchilar soni."""
        try:
            threshold = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days)
            result = await self.session.execute(
                select(func.count(User.user_id)).where(User.created_at >= threshold)
            )
            return int(result.scalar_one() or 0)
        except Exception as e:
            logger.error(
                f"❌ Yangi foydalanuvchilar sonini olishda xatolik (days={days}): {e}"
            )
            return 0
