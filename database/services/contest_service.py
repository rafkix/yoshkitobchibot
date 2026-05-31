# database/services/contest_service.py

import random
from datetime import datetime, UTC

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ReferralContest, ContestStatus, User


class ContestService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # -------------------------------------------------------
    # GET ACTIVE CONTEST
    # -------------------------------------------------------
    async def get_active_contest(self) -> ReferralContest | None:
        result = await self.session.execute(
            select(ReferralContest).where(
                ReferralContest.status == ContestStatus.ACTIVE
            )
        )
        return result.scalar_one_or_none()

    # -------------------------------------------------------
    # GET ALL CONTESTS
    # -------------------------------------------------------
    async def get_all_contests(self) -> list[ReferralContest]:
        result = await self.session.execute(
            select(ReferralContest).order_by(ReferralContest.created_at.desc())
        )
        return result.scalars().all()

    # -------------------------------------------------------
    # CREATE CONTEST
    # -------------------------------------------------------
    async def create_contest(
        self,
        title: str,
        description: str | None,
        button_text: str | None,
        min_referrals: int,
        prize_description: str | None,
    ) -> ReferralContest:
        contest = ReferralContest(
            title=title,
            description=description,
            button_text=button_text,
            min_referrals=min_referrals,
            prize_description=prize_description,
            status=ContestStatus.DRAFT,
        )
        self.session.add(contest)
        await self.session.commit()
        await self.session.refresh(contest)
        return contest

    # -------------------------------------------------------
    # START CONTEST  (draft → active)
    # -------------------------------------------------------
    async def start_contest(self, contest_id: int) -> ReferralContest | None:
        # Avval boshqa aktiv konkursni tugatamiz
        existing = await self.get_active_contest()
        if existing and existing.id != contest_id:
            existing.status = ContestStatus.FINISHED
            existing.ended_at = datetime.now(UTC)

        result = await self.session.execute(
            select(ReferralContest).where(ReferralContest.id == contest_id)
        )
        contest = result.scalar_one_or_none()
        if not contest:
            return None

        contest.status = ContestStatus.ACTIVE
        contest.started_at = datetime.now(UTC)
        await self.session.commit()
        return contest

    # -------------------------------------------------------
    # STOP CONTEST  (active → finished)
    # -------------------------------------------------------
    async def stop_contest(self, contest_id: int) -> ReferralContest | None:
        result = await self.session.execute(
            select(ReferralContest).where(ReferralContest.id == contest_id)
        )
        contest = result.scalar_one_or_none()
        if not contest:
            return None
        contest.status = ContestStatus.FINISHED
        contest.ended_at = datetime.now(UTC)
        await self.session.commit()
        return contest

    # -------------------------------------------------------
    # GET ELIGIBLE USERS
    # — Konkursda ishtirok etish shartini bajargan userlar
    #   (min_referrals ta Ro‘YXATDAN o‘TGAN referal)
    # -------------------------------------------------------
    async def get_eligible_users(self, contest: ReferralContest) -> list[User]:
        rows = await self.get_eligible_users_with_counts(contest)
        return [user for user, _ in rows]

    async def get_eligible_users_with_counts(
        self, contest: ReferralContest
    ) -> list[tuple[User, int]]:
        # Har bir userning ro‘yxatdan o‘tgan referallari soni
        subq = (
            select(
                User.referred_by.label("referrer_id"),
                func.count(User.id).label("ref_count"),
            )
            .where(User.is_registered.is_(True), User.referred_by.isnot(None))
            .group_by(User.referred_by)
            .subquery()
        )

        result = await self.session.execute(
            select(User, subq.c.ref_count)
            .join(subq, User.user_id == subq.c.referrer_id)
            .where(
                User.is_registered.is_(True),
                subq.c.ref_count >= contest.min_referrals,
            )
        )
        return [(user, int(ref_count)) for user, ref_count in result.all()]

    # -------------------------------------------------------
    # PICK RANDOM WINNER
    # -------------------------------------------------------
    async def pick_winner(self, contest_id: int) -> tuple[ReferralContest | None, User | None]:
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
        await self.session.commit()
        return contest, winner

    # -------------------------------------------------------
    # DELETE CONTEST
    # -------------------------------------------------------
    async def delete_contest(self, contest_id: int):
        result = await self.session.execute(
            select(ReferralContest).where(ReferralContest.id == contest_id)
        )
        contest = result.scalar_one_or_none()
        if contest:
            await self.session.delete(contest)
            await self.session.commit()
