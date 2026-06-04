import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import TestSession, User

logger = logging.getLogger(__name__)


class StatService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _threshold(self, days: int) -> datetime:
        return datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days)

    async def count_total_users(self) -> int:
        try:
            result = await self.session.execute(select(func.count(User.user_id)))
            return int(result.scalar_one() or 0)
        except Exception as e:
            logger.error(f"Jami userlar sonini olishda xatolik: {e}")
            return 0

    async def count_registered_users(self) -> int:
        try:
            result = await self.session.execute(
                select(func.count(User.user_id)).where(User.is_registered.is_(True))
            )
            return int(result.scalar_one() or 0)
        except Exception as e:
            logger.error(f"Registered userlar sonini olishda xatolik: {e}")
            return 0

    async def count_unregistered_users(self) -> int:
        try:
            result = await self.session.execute(
                select(func.count(User.user_id)).where(User.is_registered.is_(False))
            )
            return int(result.scalar_one() or 0)
        except Exception as e:
            logger.error(f"Unregistered userlar sonini olishda xatolik: {e}")
            return 0

    async def count_new_users_since(self, days: int) -> int:
        try:
            result = await self.session.execute(
                select(func.count(User.user_id)).where(
                    User.created_at >= self._threshold(days)
                )
            )
            return int(result.scalar_one() or 0)
        except Exception as e:
            logger.error(f"Yangi userlarni olishda xatolik: {e}")
            return 0

    async def count_new_registered_users_since(self, days: int) -> int:
        try:
            result = await self.session.execute(
                select(func.count(User.user_id)).where(
                    User.created_at >= self._threshold(days),
                    User.is_registered.is_(True),
                )
            )
            return int(result.scalar_one() or 0)
        except Exception as e:
            logger.error(f"Yangi registered userlarni olishda xatolik: {e}")
            return 0

    async def count_users_started_test(self) -> int:
        try:
            result = await self.session.execute(
                select(func.count(func.distinct(TestSession.user_id)))
            )
            return int(result.scalar_one() or 0)
        except Exception as e:
            logger.error(f"Test boshlagan userlarni olishda xatolik: {e}")
            return 0

    async def count_users_completed_test(self) -> int:
        try:
            result = await self.session.execute(
                select(func.count(func.distinct(TestSession.user_id))).where(
                    TestSession.is_completed.is_(True)
                )
            )
            return int(result.scalar_one() or 0)
        except Exception as e:
            logger.error(f"Test tugatgan userlarni olishda xatolik: {e}")
            return 0

    async def count_users_never_started_test(self) -> int:
        try:
            started_users = select(TestSession.user_id).distinct().subquery()

            result = await self.session.execute(
                select(func.count(User.user_id)).where(
                    ~User.user_id.in_(select(started_users.c.user_id))
                )
            )

            return int(result.scalar_one() or 0)

        except Exception as e:
            logger.error(f"Test ishlamagan userlarni olishda xatolik: {e}")
            return 0

    async def count_active_test_sessions(self) -> int:
        try:
            result = await self.session.execute(
                select(func.count(TestSession.id)).where(
                    TestSession.is_completed.is_(False)
                )
            )

            return int(result.scalar_one() or 0)

        except Exception as e:
            logger.error(f"Aktiv sessiyalarni olishda xatolik: {e}")
            return 0

    async def count_users_started_test_since(
        self,
        days: int,
    ) -> int:
        try:
            result = await self.session.execute(
                select(func.count(func.distinct(TestSession.user_id))).where(
                    TestSession.started_at >= self._threshold(days)
                )
            )

            return int(result.scalar_one() or 0)

        except Exception as e:
            logger.error(f"Yangi test userlarini olishda xatolik: {e}")
            return 0

    async def count_users_completed_test_since(
        self,
        days: int,
    ) -> int:
        try:
            result = await self.session.execute(
                select(func.count(func.distinct(TestSession.user_id))).where(
                    TestSession.is_completed.is_(True),
                    TestSession.completed_at >= self._threshold(days),
                )
            )

            return int(result.scalar_one() or 0)

        except Exception as e:
            logger.error(f"Yangi test yakunlagan userlarni olishda xatolik: {e}")
            return 0

    async def get_dashboard_stats(self) -> dict:
        return {
            "total_users": await self.count_total_users(),
            "registered_users": await self.count_registered_users(),
            "unregistered_users": await self.count_unregistered_users(),
            "started_test_users": await self.count_users_started_test(),
            "completed_test_users": await self.count_users_completed_test(),
            "never_started_test_users": await self.count_users_never_started_test(),
            "active_test_sessions": await self.count_active_test_sessions(),
            "new_users_24h": await self.count_new_users_since(1),
            "new_registered_24h": await self.count_new_registered_users_since(1),
            "new_test_users_24h": await self.count_users_started_test_since(1),
            "completed_test_users_24h": await self.count_users_completed_test_since(1),
        }
