# database/services/settings_service.py
"""
Bot sozlamalarini boshqarish servisi.
Admin panel orqali o'zgartiriladigan barcha sozlamalar shu yerda.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import BotSettings

# =========================================================
# DEFAULT SOZLAMALAR
# =========================================================

DEFAULT_SETTINGS = {
    "referral_score_per_user": ("1", "Har bir ro'yxatdan o'tgan referal uchun beriladigan ball"),
    "test_max_questions": ("40", "Testdagi maksimal savol soni"),
    "test_seconds_per_question": ("90", "Har bir savolga ajratiladigan vaqt (soniya)"),
    "targibot_text": (
        "🗞 <b>Targ'ibot bo'limi</b>\n\n"
        '\"Yosh kitobchi\" - 2026 yoz loyihasiga\n'
        "do'stlaringizni taklif qiling.\n\n"
        "🏆 <b>Har bir ro'yxatdan o'tgan do'st</b>\n"
        "   uchun <b>{score} ball</b> beriladi.\n\n"
        "👥 <b>Taklif qilganlar:</b> {total} ta\n"
        "✅ <b>Ro'yxatdan o'tganlar:</b> {registered} ta\n"
        "🎯 <b>Referal ballari:</b> {ref_score} ball\n\n"
        "🔗 <b>Sizning maxsus havolangiz:</b>\n\n"
        "<code>{link}</code>\n\n"
        "🔥 Eng faol targ'ibotchilar\n"
        "loyiha yakunida taqdirlanadi.",
        "Targ'ibot bo'limida ko'rsatiladigan matn"
    ),
    "welcome_unregistered_text": (
        "👋 <b>Assalomu alaykum!</b>\n\n"
        "\"Yosh kitobchi - 2026\" loyihasiga xush kelibsiz!\n\n"
        "📝 Ishtirok etish uchun ro'yxatdan o'ting.",
        "Ro'yxatdan o'tmagan foydalanuvchiga ko'rsatiladigan xabar"
    ),
    "broadcast_unregistered": (
        "False",
        "Ro'yxatdan o'tmaganlarga avtomatik xabar yuborish (True/False)"
    ),
}


class SettingsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # =====================================================
    # GET SETTING
    # =====================================================

    async def get(self, key: str, default: str | None = None) -> str | None:
        result = await self.session.execute(
            select(BotSettings).where(BotSettings.key == key)
        )
        setting = result.scalar_one_or_none()
        if setting:
            return setting.value
        # Default qiymatni qaytarish
        if key in DEFAULT_SETTINGS:
            return DEFAULT_SETTINGS[key][0]
        return default

    async def get_int(self, key: str, default: int = 0) -> int:
        val = await self.get(key)
        try:
            return int(val) if val is not None else default
        except (ValueError, TypeError):
            return default

    async def get_bool(self, key: str, default: bool = False) -> bool:
        val = await self.get(key)
        if val is None:
            return default
        return val.lower() in ("true", "1", "yes")

    # =====================================================
    # SET SETTING
    # =====================================================

    async def set(self, key: str, value: str) -> BotSettings:
        result = await self.session.execute(
            select(BotSettings).where(BotSettings.key == key)
        )
        setting = result.scalar_one_or_none()

        description = DEFAULT_SETTINGS.get(key, (None, None))[1]

        if setting:
            setting.value = value
        else:
            setting = BotSettings(key=key, value=value, description=description)
            self.session.add(setting)

        await self.session.commit()
        return setting

    # =====================================================
    # GET ALL SETTINGS
    # =====================================================

    async def get_all(self) -> list[BotSettings]:
        result = await self.session.execute(
            select(BotSettings).order_by(BotSettings.key)
        )
        db_settings = {s.key: s for s in result.scalars().all()}

        # Default sozlamalarni ham qo'shish (agar DB da yo'q bo'lsa)
        all_settings = []
        for key, (default_val, desc) in DEFAULT_SETTINGS.items():
            if key in db_settings:
                all_settings.append(db_settings[key])
            else:
                all_settings.append(
                    BotSettings(id=None, key=key, value=default_val, description=desc)
                )
        return all_settings

    # =====================================================
    # REFERRAL SCORE — tez-tez ishlatiladigan
    # =====================================================

    async def get_referral_score(self) -> int:
        return await self.get_int("referral_score_per_user", default=1)

    async def set_referral_score(self, score: int):
        await self.set("referral_score_per_user", str(score))
