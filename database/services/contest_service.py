# database/services/contest_service.py

import logging
import random
from datetime import UTC, datetime

from sqlalchemy import desc, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    ContestStatus,
    ReferralContest,
    User,
)

logger = logging.getLogger(__name__)


class ContestService:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC).replace(tzinfo=None)

    async def _save(
        self,
        contest: ReferralContest,
    ) -> ReferralContest:
        self.session.add(contest)
        await self.session.commit()
        await self.session.refresh(contest)
        return contest

    async def get_active_contest(
        self,
    ) -> ReferralContest | None:
        try:
            result = await self.session.execute(
                select(ReferralContest).where(
                    ReferralContest.status == ContestStatus.ACTIVE
                )
            )

            return result.scalar_one_or_none()

        except SQLAlchemyError as e:
            logger.error(f"Active contest olishda xatolik: {e}")
            return None

    async def get_contest_by_id(
        self,
        contest_id: int,
    ) -> ReferralContest | None:
        try:
            result = await self.session.execute(
                select(ReferralContest).where(ReferralContest.id == contest_id)
            )

            return result.scalar_one_or_none()

        except SQLAlchemyError as e:
            logger.error(f"Contest olishda xatolik: {e}")
            return None

    async def get_all_contests(
        self,
    ) -> list[ReferralContest]:
        try:
            result = await self.session.execute(
                select(ReferralContest).order_by(desc(ReferralContest.created_at))
            )

            return list(result.scalars().all())

        except SQLAlchemyError as e:
            logger.error(f"Contest list olishda xatolik: {e}")
            return []

    async def create_contest(
        self,
        title: str,
        description: str | None = None,
        button_text: str | None = None,
        min_referrals: int = 10,
        prize_description: str | None = None,
        referral_score_per_user: int = 1,
    ) -> ReferralContest | None:
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

            return await self._save(contest)

        except SQLAlchemyError as e:
            await self.session.rollback()

            logger.error(f"Contest yaratishda xatolik: {e}")

            return None

    async def start_contest(
        self,
        contest_id: int,
    ) -> ReferralContest | None:
        try:
            contest = await self.get_contest_by_id(contest_id)

            if not contest:
                return None

            await self.session.execute(
                update(ReferralContest)
                .where(ReferralContest.status == ContestStatus.ACTIVE)
                .values(
                    status=ContestStatus.FINISHED,
                    ended_at=self._now(),
                )
            )

            contest.status = ContestStatus.ACTIVE
            contest.started_at = self._now()
            contest.ended_at = None

            return await self._save(contest)

        except SQLAlchemyError as e:
            await self.session.rollback()

            logger.error(f"Contest start qilishda xatolik: {e}")

            return None

    async def stop_contest(
        self,
        contest_id: int,
    ) -> ReferralContest | None:
        try:
            contest = await self.get_contest_by_id(contest_id)

            if not contest:
                return None

            contest.status = ContestStatus.FINISHED
            contest.ended_at = self._now()

            return await self._save(contest)

        except SQLAlchemyError as e:
            await self.session.rollback()

            logger.error(f"Contest stop qilishda xatolik: {e}")

            return None

    async def update_contest(
        self,
        contest_id: int,
        *,
        title: str | None = None,
        description: str | None = None,
        button_text: str | None = None,
        min_referrals: int | None = None,
        prize_description: str | None = None,
        referral_score_per_user: int | None = None,
    ) -> ReferralContest | None:
        try:
            contest = await self.get_contest_by_id(contest_id)

            if not contest:
                return None

            if title is not None:
                contest.title = title

            if description is not None:
                contest.description = description

            if button_text is not None:
                contest.button_text = button_text

            if min_referrals is not None:
                contest.min_referrals = min_referrals

            if prize_description is not None:
                contest.prize_description = prize_description

            if referral_score_per_user is not None:
                contest.referral_score_per_user = referral_score_per_user

            return await self._save(contest)

        except SQLAlchemyError as e:
            await self.session.rollback()

            logger.error(f"Contest update xatoligi: {e}")

            return None

    async def delete_contest(
        self,
        contest_id: int,
    ) -> bool:
        try:
            contest = await self.get_contest_by_id(contest_id)

            if not contest:
                return False

            await self.session.delete(contest)
            await self.session.commit()

            return True

        except SQLAlchemyError as e:
            await self.session.rollback()

            logger.error(f"Contest delete xatoligi: {e}")

            return False

    async def get_eligible_users(
        self,
        contest_id: int,
    ) -> list[User]:
        try:
            contest = await self.get_contest_by_id(contest_id)

            if not contest:
                return []

            result = await self.session.execute(
                select(User)
                .where(
                    User.is_registered.is_(True),
                    User.referral_score
                    >= (contest.min_referrals * contest.referral_score_per_user),
                )
                .order_by(desc(User.referral_score))
            )

            return list(result.scalars().all())

        except SQLAlchemyError as e:
            logger.error(f"Eligible userlarni olishda xatolik: {e}")
            return []

    async def pick_winner(
        self,
        contest_id: int,
    ) -> tuple[
        ReferralContest | None,
        User | None,
    ]:
        try:
            contest = await self.get_contest_by_id(contest_id)

            if not contest:
                return None, None

            if contest.winner_user_id:
                result = await self.session.execute(
                    select(User).where(User.user_id == contest.winner_user_id)
                )

                return (
                    contest,
                    result.scalar_one_or_none(),
                )

            users = await self.get_eligible_users(contest_id)

            if not users:
                return contest, None

            winner = random.choice(users)

            contest.winner_user_id = winner.user_id
            contest.status = ContestStatus.FINISHED
            contest.ended_at = self._now()

            await self.session.commit()

            return contest, winner

        except SQLAlchemyError as e:
            await self.session.rollback()

            logger.error(f"Winner tanlashda xatolik: {e}")

            return None, None
