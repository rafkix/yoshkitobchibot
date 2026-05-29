# app/handlers/users/menu.py

from urllib.parse import quote
from aiogram import Router, F
from database.database import session_maker
from database.services.user_service import UserService

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQuery,
    InlineQueryResultPhoto,
    Message,
)
from database.models import ContestType, DirectionType
from main import bot

router = Router()

PROMO_IMAGE = "https://www.yoshkitobchi.uz/media/propaganda.png"

DIRECTION_LABELS = {
    DirectionType.AGE_10_14: "10-14 yosh toifasi",
    DirectionType.AGE_15_19: "15-19 yosh toifasi",
    DirectionType.AGE_20_30: "20-30 yosh toifasi",
}

MEDALS = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]


# =========================================================
# REYTING — faqat ro‘yxatdan o‘tganlar
# =========================================================

@router.message(F.text == "📊 Reyting")
async def rating_handler(message: Message) -> None:
    user_id = message.from_user.id

    async with session_maker() as session:
        service = UserService(session)
        user = await service.get_user(user_id)

        if not user:
            return await message.answer("📄 Profil topilmadi. Iltimos, ro‘yxatdan o‘ting.")

        top_users = await service.get_top_users(limit=10)

        # Foydalanuvchi ro‘yxatdan o‘tgan bo‘lsa, uning reytingini ko‘rsatamiz
        if user.is_registered:
            rank = await service.get_user_rank(user_id)
            user_rank_line = f"\n📊 <b>Sizning reytingingiz:</b> #{rank} — {user.total_score} ball"
        else:
            user_rank_line = "\n⚠️ <i>Reytingda ko‘rinish uchun ro‘yxatdan o‘ting.</i>"

    lines = ["🏆 <b>Top 10 — Eng faol ishtirokchilar</b>\n"]

    for idx, u in enumerate(top_users):
        medal = MEDALS[idx] if idx < len(MEDALS) else f"{idx + 1}."
        name = u.full_name or f"Foydalanuvchi #{u.user_id}"
        lines.append(f"{medal} {name} — {u.total_score} ball")

    lines.append(user_rank_line)
    await message.answer("\n".join(lines), parse_mode="HTML")


# =========================================================
# PROFIL
# =========================================================

@router.message(F.text == "👤 Profil")
async def profile_handler(message: Message) -> None:
    user_id = message.from_user.id

    async with session_maker() as session:
        service = UserService(session)
        user = await service.get_user(user_id)

        if not user:
            return await message.answer("📄 Profil topilmadi. Iltimos, ro‘yxatdan o‘ting.")

        referrals_total = await service.get_referrals_count(user_id)
        referrals_registered = await service.get_registered_referrals_count(user_id)
        bot_username = (await bot.me()).username
        referral_link = await service.get_referral_link(user_id, bot_username)

    contest_labels = {
        ContestType.YOSH_KITOBXON_2026: "“Yosh kitobchi” - 2026 yoz",
    }
    contest = contest_labels.get(user.contest, "—")
    direction = DIRECTION_LABELS.get(user.direction, "—")

    profile_text = (
        "<b>👤 Sizning profilingiz</b>\n\n"
        f"<b>ID:</b> <code>{user.user_id}</code>\n"
        f"<b>F.I.Sh.:</b> {user.full_name or '—'}\n"
        f"<b>Tug‘ilgan sana:</b> {user.birth_date or '—'}\n"
        f"<b>Yashash joyi:</b> {user.region or ''}, {user.district or ''}, {user.neighborhood or ''}\n"
        f"<b>Ish/o‘qish joyi:</b> {user.workplace or '—'}\n"
        f"<b>Telefon:</b> {user.phone_number or '—'}\n\n"
        f"<b>Tanlov:</b> {contest}\n"
        f"<b>Yo‘nalish:</b> {direction}\n\n"
        f"<b>🏆 Umumiy ball:</b> {user.total_score}\n"
        f"  ├ Test ballari: {user.test_score}\n"
        f"  └ Referal ballari: {user.referral_score}\n\n"
        f"<b>👥 Taklif qilganlar:</b> {referrals_total} ta kishi\n"
        f"  └ Ro‘yxatdan o‘tganlar: {referrals_registered} ta (ball berilgan)\n\n"
        f"<b>🔗 Sizning havolangiz:</b>\n<code>{referral_link}</code>"
    )

    await message.answer(profile_text, parse_mode="HTML")


# =========================================================
# TARg‘IBOT Bo‘LIMI
# =========================================================

@router.message(F.text == "🗞 Targ‘ibot")
async def advert_handler(message: Message) -> None:
    bot_username = (await bot.me()).username

    async with session_maker() as session:
        service = UserService(session)
        referral_link = await service.get_referral_link(
            user_id=message.from_user.id,
            username=bot_username,
        )
        referrals_total = await service.get_referrals_count(message.from_user.id)
        referrals_registered = await service.get_registered_referrals_count(message.from_user.id)

    share_url = (
        f"https://t.me/share/url?url={quote(referral_link)}"
        f"&text={quote('📚 "Yosh Kitobchi — 2026 yoz" loyihasiga qo\'shiling! 🏆')}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📤 Do‘stlarga ulashish",
                    switch_inline_query=referral_link,
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔗 Oddiy ulashish",
                    url=share_url,
                )
            ],
        ]
    )

    caption = (
        "🗞 <b>Targ‘ibot bo‘limi</b>\n\n"
        "“Yosh kitobchi” - 2026 yoz loyihasiga\n"
        "do‘stlaringizni taklif qiling.\n\n"
        "🏆 <b>Har bir ro‘yxatdan o‘tgan do‘st</b>\n"
        "   uchun <b>+1 ball</b> beriladi.\n\n"
        f"👥 <b>Taklif qilganlar:</b> {referrals_total} ta\n"
        f"✅ <b>Ro‘yxatdan o‘tganlar:</b> {referrals_registered} ta\n"
        f"🎯 <b>Referal ballari:</b> {referrals_registered} ball\n\n"
        f"🔗 <b>Sizning maxsus havolangiz:</b>\n\n"
        f"<code>{referral_link}</code>\n\n"
        "🔥 Eng faol targ‘ibotchilar\n"
        "loyiha yakunida taqdirlanadi."
    )

    await message.answer_photo(
        photo=PROMO_IMAGE,
        caption=caption,
        parse_mode="HTML",
        reply_markup=keyboard,
    )


# =========================================================
# INLINE SHARE
# =========================================================

@router.inline_query()
async def inline_share_handler(inline_query: InlineQuery) -> None:
    query = inline_query.query
    referral_link = "https://t.me/yoshkitobchibot"

    if query.startswith("https://t.me/"):
        referral_link = query

    text = (
        "“Yosh kitobchi” - 2026 yozloyihasiga qo‘shiling!\n\n"
        "🏆 Kitobxonlik tanlovlari\n"
        "🔥 Eng faol targ‘ibotchilar uchun sovg‘alar\n"
        "📖 Bilimingizni sinab ko‘ring va reytingda yuqorilang.\n\n"
        f"🔗 {referral_link}"
    )

    results = [
        InlineQueryResultPhoto(
            id="yoshkitobchi_share",
            photo_url=PROMO_IMAGE,
            thumbnail_url=PROMO_IMAGE,
            caption=text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="📚 Loyihaga qo‘shilish",
                            url=referral_link,
                        )
                    ]
                ]
            ),
        )
    ]

    await bot.answer_inline_query(inline_query.id, results=results, cache_time=1)
