# database/services/contest_service.py

import random
import logging
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import ReferralContest, ContestStatus, User

logger = logging.getLogger(__name__)


class ContestService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active_contest(self) -> ReferralContest | None:
        """Hozirda tizimda faol bo‘lgan jonli konkursni yuklash."""
        try:
            result = await self.session.execute(
                select(ReferralContest).where(
                    ReferralContest.status == ContestStatus.ACTIVE
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"❌ Faol konkursni yuklashda xatolik: {e}")
            return None

    async def get_all_contests(self) -> list[ReferralContest]:
        """Barcha konkurslar ro‘yxatini yangi-eskiga tartiblash."""
        try:
            result = await self.session.execute(
                select(ReferralContest).order_by(desc(ReferralContest.created_at))
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"❌ Konkurslar ro‘yxatini yuklashda xatolik: {e}")
            return []

    async def create_contest(
        self,
        title: str,
        description: str | None,
        button_text: str | None,
        min_referrals: int,
        referral_score_per_user: int = 1,
    ) -> ReferralContest | None:
        """Yangi referal konkurs yaratish (Tranzaksiyaviy xavfsiz)."""
        try:
            contest = ReferralContest(
                title=title,
                description=description,
                button_text=button_text,
                min_referrals=min_referrals,
                referral_score_per_user=referral_score_per_user,
                status=ContestStatus.ACTIVE,
            )
            self.session.add(contest)
            await self.session.commit()
            await self.session.refresh(contest)
            return contest
        except Exception as e:
            await self.session.rollback()
            logger.error(f"❌ Konkurs yaratishda xatolik: {e}")
            return None

    async def get_eligible_users_with_counts(
        self, contest: ReferralContest
    ) -> list[tuple[User, int]]:
        """Konkurs shartlarini bajargan nomzodlar ro‘yxati."""
        try:
            referrals = (
                select(
                    User.referred_by.label("referrer_id"),
                    func.count(User.user_id).label("ref_count"),
                )
                .where(
                    User.referred_by.isnot(None),
                    User.is_registered.is_(True),
                )
                .group_by(User.referred_by)
                .having(func.count(User.user_id) >= contest.min_referrals)
                .subquery()
            )

            stmt = (
                select(User, referrals.c.ref_count)
                .join(referrals, User.user_id == referrals.c.referrer_id)
                .where(User.is_registered.is_(True))
            )
            result = await self.session.execute(stmt)
            return [(row[0], int(row[1])) for row in result.all()]
        except Exception as e:
            logger.error(f"❌ Konkurs ishtirokchilarini saralashda xatolik: {e}")
            return []

    async def pick_winner(
        self, contest_id: int
    ) -> tuple[ReferralContest | None, User | None]:
        """Konkurs g‘olibini taklif qilganlar soniga mos (Weighted Random) aniqlash."""
        try:
            result = await self.session.execute(
                select(ReferralContest).where(ReferralContest.id == contest_id)
            )
            contest = result.scalar_one_or_none()
            if not contest:
                return None, None

            eligible = await self.get_eligible_users_with_counts(contest)
            if not eligible:
                return contest, None

            users = [user for user, _ in eligible]
            weights = [max(1, ref_count) for _, ref_count in eligible]

            winner = random.choices(users, weights=weights, k=1)[0]
            contest.winner_user_id = winner.user_id
            contest.status = ContestStatus.FINISHED

            self.session.add(contest)
            await self.session.commit()
            return contest, winner
        except Exception as e:
            await self.session.rollback()
            logger.error(f"❌ g‘olibni aniqlash jarayonida xatolik: {e}")
            return None, None

    async def get_min_referrals(self, contest_id: int) -> int | None:
        """Konkursning min_referrals qiymatini o‘qish."""
        try:
            result = await self.session.execute(
                select(ReferralContest.min_referrals).where(
                    ReferralContest.id == contest_id
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(
                f"❌ min_referrals ni o‘qishda xatolik (ID: {contest_id}): {e}"
            )
            return None

    async def set_min_referrals(
        self, contest_id: int, value: int
    ) -> ReferralContest | None:
        """Konkursning min_referrals qiymatini yangilash."""
        try:
            if value < 1:
                logger.warning(
                    f"⚠️ min_referrals 1 dan kichik bo‘lishi mumkin emas: {value}"
                )
                return None

            result = await self.session.execute(
                select(ReferralContest).where(ReferralContest.id == contest_id)
            )
            contest = result.scalar_one_or_none()
            if not contest:
                return None

            contest.min_referrals = value
            self.session.add(contest)
            await self.session.commit()
            await self.session.refresh(contest)
            logger.info(f"✅ min_referrals yangilandi: konkurs {contest_id} → {value}")
            return contest
        except Exception as e:
            await self.session.rollback()
            logger.error(
                f"❌ min_referrals ni yangilashda xatolik (ID: {contest_id}): {e}"
            )
            return None

    async def increment_min_referrals(
        self, contest_id: int, amount: int = 1
    ) -> ReferralContest | None:
        """min_referrals qiymatini berilgan miqdorga oshirish."""
        try:
            current = await self.get_min_referrals(contest_id)
            if current is None:
                return None
            return await self.set_min_referrals(contest_id, current + amount)
        except Exception as e:
            logger.error(
                f"❌ min_referrals ni oshirishda xatolik (ID: {contest_id}): {e}"
            )
            return None

    async def reset_min_referrals(
        self, contest_id: int, default: int = 10
    ) -> ReferralContest | None:
        """min_referrals ni standart qiymatga qaytarish."""
        return await self.set_min_referrals(contest_id, default)

    async def delete_contest(self, contest_id: int) -> bool:
        """Konkursni tizimdan butunlay o‘chirish."""
        try:
            result = await self.session.execute(
                select(ReferralContest).where(ReferralContest.id == contest_id)
            )
            contest = result.scalar_one_or_none()
            if not contest:
                return False
            await self.session.delete(contest)
            await self.session.commit()
            return True
        except Exception as e:
            await self.session.rollback()
            logger.error(f"❌ Konkursni o‘chirishda xatolik: {e}")
            return False
