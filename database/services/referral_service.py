import logging
from sqlalchemy import func, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    User,
    ReferralContest,
    ContestStatus,
)

logger = logging.getLogger(__name__)


class ReferralService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active_contest(self) -> ReferralContest | None:
        result = await self.session.execute(
            select(ReferralContest).where(
                ReferralContest.status == ContestStatus.ACTIVE
            )
        )
        return result.scalar_one_or_none()

    async def get_referral_count(
        self,
        user_id: int,
        registered_only: bool = True,
    ) -> int:
        try:
            stmt = select(func.count(User.user_id)).where(User.referred_by == user_id)

            if registered_only:
                stmt = stmt.where(User.is_registered.is_(True))

            result = await self.session.execute(stmt)

            return int(result.scalar_one() or 0)

        except Exception as e:
            logger.error(f"Referral count olishda xatolik: {e}")
            return 0

    async def get_referrals(
        self,
        user_id: int,
        registered_only: bool = True,
    ) -> list[User]:
        try:
            stmt = select(User).where(User.referred_by == user_id)

            if registered_only:
                stmt = stmt.where(User.is_registered.is_(True))

            result = await self.session.execute(stmt)

            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Referral userlarni olishda xatolik: {e}")
            return []

    async def get_referral_score_per_user(self) -> int:
        try:
            contest = await self.get_active_contest()

            if not contest:
                return 1

            return contest.referral_score_per_user

        except Exception:
            return 1

    async def add_referral_points(
        self,
        user_id: int,
        points: int,
    ) -> bool:
        try:
            await self.session.execute(
                update(User)
                .where(User.user_id == user_id)
                .values(
                    referral_score=User.referral_score + points,
                    total_score=User.total_score + points,
                )
            )

            await self.session.commit()

            return True

        except Exception as e:
            await self.session.rollback()

            logger.error(f"Referral score qo‘shishda xatolik: {e}")

            return False

    async def set_referral_score(
        self,
        user_id: int,
        score: int,
    ) -> bool:
        try:
            user_result = await self.session.execute(
                select(User).where(User.user_id == user_id)
            )

            user = user_result.scalar_one_or_none()

            if not user:
                return False

            user.referral_score = score
            user.total_score = user.test_score + user.referral_score

            await self.session.commit()

            return True

        except Exception as e:
            await self.session.rollback()

            logger.error(f"Referral score o‘rnatishda xatolik: {e}")

            return False

    async def recalculate_user_score(
        self,
        user_id: int,
    ) -> bool:
        try:
            user_result = await self.session.execute(
                select(User).where(User.user_id == user_id)
            )

            user = user_result.scalar_one_or_none()

            if not user:
                return False

            referral_count = await self.get_referral_count(
                user_id=user.user_id,
                registered_only=True,
            )

            score_per_user = await self.get_referral_score_per_user()

            user.referral_score = referral_count * score_per_user

            user.total_score = user.test_score + user.referral_score

            await self.session.commit()

            return True

        except Exception as e:
            await self.session.rollback()

            logger.error(f"User referral score recalculation xatoligi: {e}")

            return False

    async def recalculate_all_referral_scores(
        self,
    ) -> int:
        try:
            users_result = await self.session.execute(
                select(User).where(User.is_registered.is_(True))
            )

            users = users_result.scalars().all()

            score_per_user = await self.get_referral_score_per_user()

            updated = 0

            for user in users:
                referral_count = await self.get_referral_count(
                    user.user_id,
                    registered_only=True,
                )

                user.referral_score = referral_count * score_per_user

                user.total_score = user.test_score + user.referral_score

                updated += 1

            await self.session.commit()

            return updated

        except Exception as e:
            await self.session.rollback()

            logger.error(f"Mass recalculation xatoligi: {e}")

            return 0

    async def get_leaderboard(
        self,
        limit: int = 20,
    ) -> list[User]:
        try:
            result = await self.session.execute(
                select(User)
                .where(User.is_registered.is_(True))
                .order_by(
                    desc(User.referral_score),
                    desc(User.total_score),
                )
                .limit(limit)
            )

            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Leaderboard olishda xatolik: {e}")
            return []

    async def get_top_referrers(
        self,
        limit: int = 20,
    ):
        try:
            referrals = (
                select(
                    User.referred_by.label("referrer_id"),
                    func.count(User.user_id).label("ref_count"),
                )
                .where(
                    User.referred_by.is_not(None),
                    User.is_registered.is_(True),
                )
                .group_by(User.referred_by)
                .subquery()
            )

            result = await self.session.execute(
                select(
                    User,
                    referrals.c.ref_count,
                )
                .join(
                    referrals,
                    User.user_id == referrals.c.referrer_id,
                )
                .order_by(desc(referrals.c.ref_count))
                .limit(limit)
            )

            return [
                (
                    row[0],
                    int(row[1]),
                )
                for row in result.all()
            ]

        except Exception as e:
            logger.error(f"Top referrers olishda xatolik: {e}")
            return []

    async def get_referral_link(
        self,
        user_id: int,
        bot_username: str,
    ) -> str:
        return f"https://t.me/{bot_username}?start={user_id}"

    async def get_user_referral_stats(
        self,
        user_id: int,
    ) -> dict:
        referral_count = await self.get_referral_count(
            user_id=user_id,
            registered_only=True,
        )

        user_result = await self.session.execute(
            select(User).where(User.user_id == user_id)
        )

        user = user_result.scalar_one_or_none()

        if not user:
            return {}

        return {
            "referral_count": referral_count,
            "referral_score": user.referral_score,
            "total_score": user.total_score,
            "test_score": user.test_score,
        }
