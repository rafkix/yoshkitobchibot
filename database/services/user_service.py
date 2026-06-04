import logging
from datetime import UTC, datetime

from sqlalchemy import String, cast, desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User

logger = logging.getLogger(__name__)

DEFAULT_REFERRAL_SCORE_PER_USER = 1

ALLOWED_UPDATE_FIELDS = {
    "full_name",
    "birth_date",
    "phone_number",
    "region",
    "district",
    "neighborhood",
    "workplace",
    "contest",
    "direction",
    "is_registered",
}


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _recalculate_score(user: User) -> None:
        user.total_score = user.test_score + user.referral_score

    async def _commit(self) -> bool:
        try:
            await self.session.commit()
            return True
        except Exception:
            await self.session.rollback()
            raise

    async def _save_user(self, user: User) -> User | None:
        try:
            self._recalculate_score(user)
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
            return user
        except Exception as e:
            await self.session.rollback()
            logger.error(f"User saqlashda xatolik: {e}")
            return None

    async def get_user(self, user_id: int) -> User | None:
        try:
            result = await self.session.execute(
                select(User).where(User.user_id == user_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"User olishda xatolik ({user_id}): {e}")
            return None

    async def get_all_users(self, registered_only: bool = False) -> list[User]:
        try:
            stmt = select(User).order_by(desc(User.created_at))

            if registered_only:
                stmt = stmt.where(User.is_registered.is_(True))

            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Userlar ro‘yxatini olishda xatolik: {e}")
            return []

    async def create_user(
        self,
        user_id: int,
        referred_by: int | None = None,
    ) -> User | None:
        try:
            existing = await self.get_user(user_id)

            if existing:
                return existing

            if referred_by == user_id:
                referred_by = None

            if referred_by:
                referrer = await self.get_user(referred_by)
                if not referrer:
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
            logger.error(f"User yaratishda xatolik ({user_id}): {e}")
            return None

    async def update_referred_by(
        self,
        user_id: int,
        referred_by: int,
    ) -> bool:
        try:
            if user_id == referred_by:
                return False

            referrer = await self.get_user(referred_by)

            if not referrer:
                return False

            result = await self.session.execute(
                update(User)
                .where(
                    User.user_id == user_id,
                    User.referred_by.is_(None),
                )
                .values(referred_by=referred_by)
            )

            await self.session.commit()

            return result.rowcount > 0

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Referrer update xatoligi: {e}")
            return False

    async def _get_referral_bonus(self) -> int:
        try:
            from database.services.contest_service import ContestService

            contest = await ContestService(self.session).get_active_contest()

            if contest:
                return contest.referral_score_per_user

        except Exception as e:
            logger.warning(f"Referral bonus olishda xatolik: {e}")

        return DEFAULT_REFERRAL_SCORE_PER_USER

    async def _notify_referrer(
        self,
        bot,
        referrer_id: int,
        full_name: str,
        bonus: int,
    ) -> None:
        if not bot:
            return

        try:
            await bot.send_message(
                chat_id=referrer_id,
                text=(
                    f"🎉 <b>Tabriklaymiz!</b>\n\n"
                    f"Siz taklif qilgan <b>{full_name}</b> "
                    f"ro‘yxatdan o‘tdi.\n\n"
                    f"✅ Sizga <b>+{bonus} ball</b> berildi."
                ),
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning(f"Xabar yuborishda xatolik: {e}")

    async def complete_registration(
        self,
        user_id: int,
        bot=None,
        **kwargs,
    ) -> User | None:
        try:
            user = await self.get_user(user_id)

            if not user:
                return None

            for key, value in kwargs.items():
                if key in ALLOWED_UPDATE_FIELDS:
                    setattr(user, key, value)

            first_registration = not user.is_registered

            referrer = None
            bonus = 0
            full_name = kwargs.get("full_name") or f"#{user_id}"

            if first_registration:
                user.is_registered = True

                if user.referred_by:
                    referrer = await self.get_user(user.referred_by)

                    if referrer and referrer.is_registered:
                        bonus = await self._get_referral_bonus()

                        # ✅ FIX: Referrer scoring o‘zgartirildi - to‘g‘rida commit qilish kerak
                        await self.session.execute(
                            update(User)
                            .where(User.user_id == referrer.user_id)
                            .values(
                                referral_score=User.referral_score + bonus,
                                total_score=User.total_score + bonus,
                            )
                        )
                        await self.session.commit()

            saved_user = await self._save_user(user)

            if saved_user and bot and first_registration and referrer and bonus > 0:
                await self._notify_referrer(
                    bot=bot,
                    referrer_id=referrer.user_id,
                    full_name=full_name,
                    bonus=bonus,
                )

            return saved_user

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Registration xatoligi ({user_id}): {e}")
            return None

    async def update_user(
        self,
        user_id: int,
        **kwargs,
    ) -> User | None:
        try:
            user = await self.get_user(user_id)

            if not user:
                return None

            for key, value in kwargs.items():
                if key in ALLOWED_UPDATE_FIELDS:
                    setattr(user, key, value)

            return await self._save_user(user)

        except Exception as e:
            await self.session.rollback()
            logger.error(f"User update xatoligi ({user_id}): {e}")
            return None

    async def add_referral_score(
        self,
        user_id: int,
        score: int,
    ) -> User | None:
        try:
            await self.session.execute(
                update(User)
                .where(User.user_id == user_id)
                .values(
                    referral_score=User.referral_score + score,
                    total_score=User.total_score + score,
                )
            )

            await self.session.commit()

            return await self.get_user(user_id)

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Referral score qo‘shishda xatolik: {e}")
            return None

    async def set_referral_score(
        self,
        user_id: int,
        score: int,
    ) -> User | None:
        try:
            user = await self.get_user(user_id)

            if not user:
                return None

            user.referral_score = score

            return await self._save_user(user)

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Referral score o‘rnatishda xatolik: {e}")
            return None

    async def get_referrals_count(self, user_id: int) -> int:
        try:
            result = await self.session.execute(
                select(func.count(User.user_id)).where(User.referred_by == user_id)
            )
            return int(result.scalar_one() or 0)
        except Exception:
            return 0

    async def get_registered_referrals_count(self, user_id: int) -> int:
        try:
            result = await self.session.execute(
                select(func.count(User.user_id)).where(
                    User.referred_by == user_id,
                    User.is_registered.is_(True),
                )
            )
            return int(result.scalar_one() or 0)
        except Exception:
            return 0

    async def get_top_users(self, limit: int = 10) -> list[User]:
        try:
            result = await self.session.execute(
                select(User)
                .where(User.is_registered.is_(True))
                .order_by(
                    desc(User.total_score),
                    User.created_at.asc(),
                )
                .limit(limit)
            )

            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Top userlarni olishda xatolik: {e}")
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

            return result.scalar() or 0

        except Exception as e:
            logger.error(f"Rank olishda xatolik: {e}")
            return 0

    async def get_referral_link(
        self,
        user_id: int,
        username: str | None = None,
    ) -> str:
        return f"https://t.me/{username}?start={user_id}"

    async def search_users(self, query: str) -> list[User]:
        try:
            result = await self.session.execute(
                select(User).where(
                    or_(
                        User.full_name.ilike(f"%{query}%"),
                        User.phone_number.ilike(f"%{query}%"),
                        cast(User.user_id, String).ilike(f"%{query}%"),
                    )
                )
            )

            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Qidiruv xatoligi: {e}")
            return []

    async def get_user_by_phone(
        self,
        phone: str,
    ) -> User | None:
        try:
            result = await self.session.execute(
                select(User).where(User.phone_number == phone)
            )

            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Telefon bo‘yicha qidiruv xatoligi: {e}")
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
            logger.error(f"User o‘chirishda xatolik: {e}")
            return False
