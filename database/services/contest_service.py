import random
import logging
from datetime import datetime
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import ReferralContest, ContestStatus, User

logger = logging.getLogger(__name__)


class ContestService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active_contest(self) -> ReferralContest | None:
        """Hozirda tizimda faol (Aktiv) bo‘lgan konkursni qaytaradi."""
        try:
            result = await self.session.execute(
                select(ReferralContest).where(
                    ReferralContest.status == ContestStatus.ACTIVE
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Faol konkursni yuklashda xatolik: {e}")
            return None

    async def get_contest_by_id(self, contest_id: int) -> ReferralContest | None:
        """Konkursni ID bo‘yicha tezkor yuklash (Optimallashgan)."""
        try:
            result = await self.session.execute(
                select(ReferralContest).where(ReferralContest.id == contest_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Konkursni ID bo‘yicha olishda xatolik: {e}")
            return None

    async def get_all_contests(self) -> list[ReferralContest]:
        """Barcha yaratilgan konkurslar ro‘yxatini vaqti bo‘yicha saralab beradi."""
        try:
            result = await self.session.execute(
                select(ReferralContest).order_by(desc(ReferralContest.created_at))
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Konkurslar ro‘yxatini yuklashda xatolik: {e}")
            return []

    async def create_contest(
        self,
        title: str,
        description: str | None,
        button_text: str | None,
        min_referrals: int = 10,
        prize_description: str | None = None,
        referral_score_per_user: int = 1,
    ) -> ReferralContest | None:
        """Yangi qoralama (DRAFT) holatidagi konkurs yaratish."""
        try:
            contest = ReferralContest(
                title=title,
                description=description,
                button_text=button_text,
                min_referrals=min_referrals,
                prize_description=prize_description,
                referral_score_per_user=referral_score_per_user,
                status=ContestStatus.DRAFT,
            )
            self.session.add(contest)
            await self.session.commit()
            await self.session.refresh(contest)
            return contest
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Konkurs yaratishda xatolik: {e}")
            return None

    async def start_contest(self, contest_id: int) -> ReferralContest | None:
        """Konkursni ACTIVE holatga o‘tkazadi va vaqtini belgilaydi."""
        try:
            contest = await self.get_contest_by_id(contest_id)
            if not contest:
                return None

            contest.status = ContestStatus.ACTIVE
            contest.started_at = datetime.now()
            await self.session.commit()
            await self.session.refresh(contest)
            return contest
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Konkursni faollashtirishda xatolik: {e}")
            return None

    async def stop_contest(self, contest_id: int) -> ReferralContest | None:
        """Konkursni FINISHED holatiga o‘tkazadi."""
        try:
            contest = await self.get_contest_by_id(contest_id)
            if not contest:
                return None

            contest.status = ContestStatus.FINISHED
            contest.ended_at = datetime.now()
            await self.session.commit()
            await self.session.refresh(contest)
            return contest
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Konkursni to‘xtatishda xatolik: {e}")
            return None

    async def get_eligible_users_with_counts(
        self, contest: ReferralContest
    ) -> list[tuple[User, int]]:
        """Konkursning minimal referal shartini bajargan foydalanuvchilar ro‘yxati."""
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
            logger.error(f"Ishtirokchilarni hisoblashda xatolik: {e}")
            return []

    async def pick_winner(
        self, contest_id: int
    ) -> tuple[ReferralContest | None, User | None]:
        """Weighted Random algoritmi orqali g‘olibni aniqlash."""
        try:
            contest = await self.get_contest_by_id(contest_id)
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
            contest.ended_at = datetime.now()

            await self.session.commit()
            return contest, winner
        except Exception as e:
            await self.session.rollback()
            logger.error(f"g‘olibni aniqlashda xatolik: {e}")
            return None, None

    async def delete_contest(self, contest_id: int) -> bool:
        """Konkursni bazadan butunlay o‘chirish."""
        try:
            contest = await self.get_contest_by_id(contest_id)
            if not contest:
                return False
            await self.session.delete(contest)
            await self.session.commit()
            return True
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Konkursni o‘chirishda xatolik: {e}")
            return False
