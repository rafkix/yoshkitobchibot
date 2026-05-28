from sqlalchemy import select, update, delete, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, ContestType, DirectionType


# =========================================================
# USER SERVICE
# =========================================================


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # =====================================================
    # GET USER
    # =====================================================

    async def get_user(self, user_id: int) -> User | None:
        result = await self.session.execute(select(User).where(User.user_id == user_id))
        return result.scalar_one_or_none()

    # =====================================================
    # CREATE USER
    # =====================================================

    async def create_user(self, user_id: int, referred_by: int | None = None) -> User:
        existing = await self.get_user(user_id)
        if existing:
            return existing

        user = User(user_id=user_id, referred_by=referred_by)
        self.session.add(user)

        if referred_by and referred_by != user_id:
            referrer = await self.get_user(referred_by)
            if referrer:
                referrer.referral_score += 1
                referrer.total_score += 1

        await self.session.commit()
        return user

    # =====================================================
    # UPDATE USER
    # =====================================================

    async def update_user(self, user_id: int, **kwargs):
        await self.session.execute(
            update(User).where(User.user_id == user_id).values(**kwargs)
        )
        await self.session.commit()

    # =====================================================
    # COMPLETE REGISTRATION
    # =====================================================

    async def complete_registration(
        self,
        user_id: int,
        full_name: str,
        birth_date,
        phone_number: str,
        region: str,
        district: str,
        neighborhood: str,
        workplace: str,
        contest: ContestType,
        direction: DirectionType,
    ):
        await self.update_user(
            user_id=user_id,
            full_name=full_name,
            birth_date=birth_date,
            phone_number=phone_number,
            region=region,
            district=district,
            neighborhood=neighborhood,
            workplace=workplace,
            contest=contest,
            direction=direction,
            is_registered=True,
        )

    # =====================================================
    # ADD TEST SCORE
    # =====================================================

    async def add_test_score(self, user_id: int, score: int):
        user = await self.get_user(user_id)
        if not user:
            return
        user.test_score += score
        user.total_score += score
        await self.session.commit()

    # =====================================================
    # ADD REFERRAL SCORE
    # =====================================================

    async def add_referral_score(self, user_id: int, score: int = 1):
        user = await self.get_user(user_id)
        if not user:
            return
        user.referral_score += score
        user.total_score += score
        await self.session.commit()

    # =====================================================
    # GET USER RANK
    # =====================================================

    async def get_user_rank(self, user_id: int):
        subquery = select(
            User.user_id,
            func.rank().over(order_by=desc(User.total_score)).label("rank"),
        ).subquery()

        result = await self.session.execute(
            select(subquery.c.rank).where(subquery.c.user_id == user_id)
        )
        return result.scalar() or "N/A"

    # =====================================================
    # GET TOP USERS
    # =====================================================

    async def get_top_users(self, limit: int = 10):
        result = await self.session.execute(
            select(User).order_by(desc(User.total_score)).limit(limit)
        )
        return result.scalars().all()

    # =====================================================
    # GET USERS COUNT
    # =====================================================

    async def get_users_count(self):
        result = await self.session.execute(select(func.count(User.id)))
        return result.scalar()

    # =====================================================
    # GET REFERRALS COUNT
    # =====================================================

    async def get_referrals_count(self, user_id: int):
        result = await self.session.execute(
            select(func.count(User.id)).where(User.referred_by == user_id)
        )
        return result.scalar()

    # =====================================================
    # GET REFERRAL LINK
    # =====================================================

    async def get_referral_link(self, user_id: int, username: str | None = None) -> str:
        bot_username = username or "yoshkitobchibot"
        return f"https://t.me/{bot_username}?start={user_id}"

    # =====================================================
    # DELETE USER
    # =====================================================

    async def delete_user(self, user_id: int):
        await self.session.execute(delete(User).where(User.user_id == user_id))
        await self.session.commit()
