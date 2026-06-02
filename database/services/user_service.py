# database/services/user_service.py

import logging
from datetime import datetime, UTC
from sqlalchemy import select, func, desc, or_, update
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User

logger = logging.getLogger(__name__)

DEFAULT_REFERRAL_SCORE_PER_USER = 1


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user(self, user_id: int) -> User | None:
        try:
            result = await self.session.execute(
                select(User).where(User.user_id == user_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"❌ Foydalanuvchini olishda xatolik (ID: {user_id}): {e}")
            return None

    async def get_all_users(self, registered_only: bool = False) -> list[User]:
        try:
            query = select(User).order_by(desc(User.created_at))
            if registered_only:
                query = query.where(User.is_registered.is_(True))
            result = await self.session.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"❌ Barcha foydalanuvchilarni yuklashda xatolik: {e}")
            return []

    async def create_user(
        self, user_id: int, referred_by: int | None = None
    ) -> User | None:
        try:
            if referred_by and int(referred_by) == int(user_id):
                referred_by = None

            if referred_by:
                referrer_exists = await self.get_user(referred_by)
                if not referrer_exists:
                    referred_by = None

            user = User(
                user_id=user_id,
                referred_by=referred_by,
                created_at=datetime.now(UTC).replace(tzinfo=None),
            )
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
            return user
        except Exception as e:
            await self.session.rollback()
            logger.error(f"❌ Foydalanuvchi ochishda xatolik (ID: {user_id}): {e}")
            return None

    async def update_referred_by(self, user_id: int, referred_by: int) -> bool:
        try:
            if referred_by == user_id:
                return False

            referrer = await self.get_user(referred_by)
            if not referrer:
                logger.warning(
                    f"⚠️ update_referred_by: referrer {referred_by} topilmadi"
                )
                return False

            result = await self.session.execute(
                update(User)
                .where(User.user_id == user_id, User.referred_by.is_(None))
                .values(referred_by=referred_by)
            )
            await self.session.commit()

            updated = result.rowcount > 0
            if updated:
                logger.info(
                    f"✅ referred_by yangilandi: user {user_id} → referrer {referred_by}"
                )
            return updated
        except Exception as e:
            await self.session.rollback()
            logger.error(f"❌ referred_by yangilashda xatolik (user: {user_id}): {e}")
            return False

    async def _get_referral_bonus(self) -> int:
        try:
            from database.services.contest_service import ContestService

            active_contest = await ContestService(self.session).get_active_contest()
            if active_contest:
                return active_contest.referral_score_per_user
        except Exception as e:
            logger.warning(f"⚠️ Konkurs balini olishda xatolik: {e}")

        return DEFAULT_REFERRAL_SCORE_PER_USER

    async def complete_registration(
        self,
        user_id: int,
        bot=None,
        **kwargs,
    ) -> User | None:
        """Ro‘yxatdan o‘tishni yakunlash va referal uchun taklif qilganga ball + xabar."""
        try:
            user = await self.get_user(user_id)
            if not user:
                return None

            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)

            if not user.is_registered:
                user.is_registered = True

                if user.referred_by:
                    referrer = await self.get_user(user.referred_by)
                    if referrer and referrer.is_registered:
                        bonus = await self._get_referral_bonus()
                        referrer.referral_score += bonus
                        referrer.total_score = (
                            referrer.test_score + referrer.referral_score
                        )
                        self.session.add(referrer)
                        logger.info(
                            f"✅ Referal ball: user {user.referred_by} ga +{bonus} ball "
                            f"(yangi foydalanuvchi: {user_id})"
                        )

                        # ✅ Referrerga xabar yuborish
                        if bot:
                            try:
                                new_user_name = kwargs.get("full_name") or f"#{user_id}"
                                await bot.send_message(
                                    chat_id=referrer.user_id,
                                    text=(
                                        f"🎉 <b>Tabriklaymiz!</b>\n\n"
                                        f"Siz taklif qilgan <b>{new_user_name}</b> "
                                        f"ro‘yxatdan o‘tdi.\n\n"
                                        f"✅ Sizga <b>+{bonus} ball</b> berildi!\n"
                                        f"🎯 Jami referal ballaringiz: "
                                        f"<b>{referrer.referral_score}</b>"
                                    ),
                                    parse_mode="HTML",
                                )
                            except Exception as e:
                                logger.warning(
                                    f"⚠️ Referrerga xabar yuborishda xatolik "
                                    f"(ID: {referrer.user_id}): {e}"
                                )

            user.total_score = user.test_score + user.referral_score
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
            return user
        except Exception as e:
            await self.session.rollback()
            logger.error(
                f"❌ Ro‘yxatdan o‘tishni yakunlashda xatolik (ID: {user_id}): {e}"
            )
            return None

    async def update_user(self, user_id: int, **kwargs) -> User | None:
        try:
            user = await self.get_user(user_id)
            if not user:
                return None

            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)

            user.total_score = user.test_score + user.referral_score
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
            return user
        except Exception as e:
            await self.session.rollback()
            logger.error(f"❌ Profilni yangilashda xatolik (ID: {user_id}): {e}")
            return None

    async def add_referral_score(self, user_id: int, score: int) -> User | None:
        try:
            user = await self.get_user(user_id)
            if not user:
                return None

            user.referral_score += score
            user.total_score = user.test_score + user.referral_score
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
            return user
        except Exception as e:
            await self.session.rollback()
            logger.error(f"❌ Referal ballni qo‘shishda xatolik (ID: {user_id}): {e}")
            return None

    async def set_referral_score(self, user_id: int, score: int) -> User | None:
        try:
            user = await self.get_user(user_id)
            if not user:
                return None

            user.referral_score = score
            user.total_score = user.test_score + user.referral_score
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
            return user
        except Exception as e:
            await self.session.rollback()
            logger.error(f"❌ Referal ballni o‘rnatishda xatolik (ID: {user_id}): {e}")
            return None

    async def get_referrals_count(self, user_id: int) -> int:
        try:
            result = await self.session.execute(
                select(func.count(User.user_id)).where(User.referred_by == user_id)
            )
            return int(result.scalar_one() or 0)
        except Exception as e:
            logger.error(f"❌ Referallar sonini olishda xatolik (ID: {user_id}): {e}")
            return 0

    async def get_registered_referrals_count(self, user_id: int) -> int:
        try:
            result = await self.session.execute(
                select(func.count(User.user_id)).where(
                    User.referred_by == user_id, User.is_registered.is_(True)
                )
            )
            return int(result.scalar_one() or 0)
        except Exception as e:
            logger.error(
                f"❌ Faol referallar sonini olishda xatolik (ID: {user_id}): {e}"
            )
            return 0

    async def get_top_users(self, limit: int = 10) -> list[User]:
        try:
            result = await self.session.execute(
                select(User)
                .where(User.is_registered.is_(True))
                .order_by(desc(User.total_score), User.created_at.asc())
                .limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"❌ Top foydalanuvchilarni yuklashda xatolik: {e}")
            return []

    async def get_user_rank(self, user_id: int) -> int:
        try:
            subq = (
                select(
                    User.user_id,
                    func.rank().over(order_by=desc(User.total_score)).label("rank"),
                )
                .where(User.is_registered.is_(True))
                .subquery()
            )
            result = await self.session.execute(
                select(subq.c.rank).where(subq.c.user_id == user_id)
            )
            rank = result.scalar()
            return rank if rank is not None else 0
        except Exception as e:
            logger.error(f"❌ Reyting o‘rnini aniqlashda xatolik (ID: {user_id}): {e}")
            return 0

    async def get_referral_link(self, user_id: int, username: str | None = None) -> str:
        return f"https://t.me/{username}?start={user_id}"

    async def search_users(self, query: str) -> list[User]:
        try:
            result = await self.session.execute(
                select(User).where(
                    or_(
                        User.full_name.ilike(f"%{query}%"),
                        User.phone_number.ilike(f"%{query}%"),
                        func.cast(User.user_id, func.text).ilike(f"%{query}%"),
                    )
                )
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"❌ Qidiruvda xatolik (Query: {query}): {e}")
            return []

    async def get_user_by_phone(self, phone: str) -> User | None:
        try:
            result = await self.session.execute(
                select(User).where(User.phone_number == phone)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"❌ Telefon bo‘yicha foydalanuvchi qidirishda xatolik: {e}")
            return None

    async def delete_user(self, user_id: int) -> bool:
        try:
            user = await self.get_user(user_id)
            if not user:
                return False
            await self.session.delete(user)
            await self.session.commit()
            return True
        except Exception as e:
            await self.session.rollback()
            logger.error(f"❌ Foydalanuvchini o‘chirishda xatolik (ID: {user_id}): {e}")
            return False
