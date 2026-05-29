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
    # GET ALL USERS
    # =====================================================

    async def get_all_users(self, registered_only: bool = False) -> list[User]:
        query = select(User).order_by(desc(User.created_at))
        if registered_only:
            query = query.where(User.is_registered.is_(True))
        result = await self.session.execute(query)
        return result.scalars().all()

    # =====================================================
    # CREATE USER
    # =====================================================

    async def create_user(self, user_id: int, referred_by: int | None = None) -> User:
        existing = await self.get_user(user_id)
        if existing:
            return existing

        user = User(user_id=user_id, referred_by=referred_by)
        self.session.add(user)
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
    # — Ro‘yxatdan o‘tish tugaganda referal ball beriladi
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
        user = await self.get_user(user_id)
        if not user:
            return

        # Foydalanuvchi oldin ro‘yxatdan o‘tmagan bo‘lsa referal balini beramiz
        if not user.is_registered and user.referred_by:
            referrer = await self.get_user(user.referred_by)
            if referrer and referrer.user_id != user_id:
                referrer.referral_score += 1
                referrer.total_score += 1

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
    # ADD REFERRAL SCORE (manual, admin uchun)
    # =====================================================

    async def add_referral_score(self, user_id: int, score: int = 1):
        user = await self.get_user(user_id)
        if not user:
            return
        user.referral_score += score
        user.total_score += score
        await self.session.commit()

    # =====================================================
    # GET USER RANK — faqat ro‘yxatdan o‘tganlar orasida
    # =====================================================

    async def get_user_rank(self, user_id: int) -> int | str:
        subquery = (
            select(
                User.user_id,
                func.rank()
                .over(order_by=desc(User.total_score))
                .label("rank"),
            )
            .where(User.is_registered.is_(True))
            .subquery()
        )

        result = await self.session.execute(
            select(subquery.c.rank).where(subquery.c.user_id == user_id)
        )
        return result.scalar() or "N/A"

    # =====================================================
    # GET TOP USERS — faqat ro‘yxatdan o‘tganlar
    # =====================================================

    async def get_top_users(self, limit: int = 10) -> list[User]:
        result = await self.session.execute(
            select(User)
            .where(User.is_registered.is_(True))
            .order_by(desc(User.total_score))
            .limit(limit)
        )
        return result.scalars().all()

    # =====================================================
    # GET USERS COUNT
    # =====================================================

    async def get_users_count(self) -> int:
        result = await self.session.execute(select(func.count(User.id)))
        return result.scalar() or 0

    # =====================================================
    # GET REFERRALS COUNT — nechta odam bu user orqali kelgan
    # =====================================================

    async def get_referrals_count(self, user_id: int) -> int:
        result = await self.session.execute(
            select(func.count(User.id)).where(User.referred_by == user_id)
        )
        return result.scalar() or 0

    # =====================================================
    # GET REGISTERED REFERRALS COUNT
    # — ro‘yxatdan o‘tgan referallar (ball bergan)
    # =====================================================

    async def get_registered_referrals_count(self, user_id: int) -> int:
        result = await self.session.execute(
            select(func.count(User.id)).where(
                User.referred_by == user_id,
                User.is_registered.is_(True),
            )
        )
        return result.scalar() or 0

    # =====================================================
    # GET REFERRAL LINK
    # =====================================================

    async def get_referral_link(self, user_id: int, username: str | None = None) -> str:
        bot_username = username or "yoshkitobchibot"
        return f"https://t.me/{bot_username}?start={user_id}"

    # =====================================================
    # SEARCH USERS — admin uchun qidiruv
    # =====================================================

    async def search_users(self, query: str) -> list[User]:
        """
        Ism, telefon yoki user_id bo‘yicha qidiradi.
        """
        result = await self.session.execute(
            select(User).where(
                User.full_name.ilike(f"%{query}%")
                | User.phone_number.ilike(f"%{query}%")
            )
        )
        return result.scalars().all()

    async def get_user_by_phone(self, phone: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.phone_number == phone)
        )
        return result.scalar_one_or_none()

    # =====================================================
    # DELETE USER
    # =====================================================

    async def delete_user(self, user_id: int):
        await self.session.execute(delete(User).where(User.user_id == user_id))
        await self.session.commit()
