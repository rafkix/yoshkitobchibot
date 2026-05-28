# app/handlers/users/menu.py

"""Handlers for main menu buttons.

This module provides simple placeholder responses for the main menu
buttons defined in ``app.keyboards.reply.main_menu_keyboard``.
"""

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
from database.models import ContestType
from main import bot

share_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📤 Ulashish",
                switch_inline_query=(
                    "📚 “Yosh Kitobchi — 2026 yoz” loyihasiga qo‘shiling!\n\n"
                    "🏆 Kitobxonlik tanlovlari\n"
                    "🎯 Bonus ballar\n"
                    "🔥 Faol targ‘ibotchilar uchun sovg‘alar"
                ),
            )
        ]
    ]
)

router = Router()


# @router.message(F.text == "📄 Test")
# async def test_handler(message: Message) -> None:
#     """Handle the "Test" button.

#     Currently a placeholder – you can replace the text with the real implementation.
#     """
#     await message.answer("🧪 Test bo‘limi hali ishlab chiqilmoqda.")


@router.message(F.text == "📊 Reyting")
async def rating_handler(message: Message) -> None:
    """Handle the "Reyting" button.

    Shows the user's ranking and top users.
    """
    user_id = message.from_user.id
    async with session_maker() as session:
        user_service = UserService(session)
        user = await user_service.get_user(user_id)
        if not user:
            await message.answer("📄 Profil topilmadi. Iltimos, ro‘yxatdan o‘ting.")
        else:
            rank = await user_service.get_user_rank(user_id)
            top_users = await user_service.get_top_users(limit=10)
            lines = [
                f"🏆 <b>Umumiy reytinging</b>",
                "",
                "🔝 <b>Top 10 foydalanuvchilar</b>:",
            ]
            for idx, u in enumerate(top_users, start=1):
                name = u.full_name or f"ID {u.user_id}"
                lines.append(f"{idx}. {name} — {u.total_score} ball")

            # Append user's ranking after the top list
            lines.append("")
            lines.append(f"📊 <b>Sizning reytingingiz:</b> {user.total_score} #{rank}")
            rating_text = "\n".join(lines)
            await message.answer(rating_text, parse_mode="HTML")


@router.message(F.text == "👤 Profil")
async def profile_handler(message: Message) -> None:
    """Handle the "Profil" button.

    Shows the user's profile information from the database.
    """
    user_id = message.from_user.id
    # Open a DB session and fetch user data
    async with session_maker() as session:
        user_service = UserService(session)
        user = await user_service.get_user(user_id)
        if not user:
            await message.answer("📄 Profil topilmadi. Iltimos, ro‘yxatdan o‘ting.")
            return

        # Contest and direction display
        contest_labels = {
            ContestType.YOSH_KITOBXON_2026: "“Yosh kitobxon” tanlovi 2026",
        }
        contest = contest_labels.get(user.contest, "Yo‘q")

        profile_text = (
            f"<b>Sizning ma‘lumotlaringiz:</b>\n\n"
            f"<b>ID:</b> <code>{user.user_id}</code>\n"
            f"<b>F.I.Sh.:</b> {user.full_name or 'N/A'}\n"
            f"<b>Yashash joyi:</b> {user.region or ''}, {user.district or ''}, {user.neighborhood or ''}\n\n"
            f"<b>Telefon:</b> {user.phone_number or 'N/A'}\n"
            f"<b>Tanlov:</b> {contest}\n"
            f"<b>Umumiy ball:</b> {user.total_score}"
        )
        await message.answer(profile_text, parse_mode="HTML")


# =========================================================
# TARG‘IBOT BO‘LIMI
# =========================================================
PROMO_IMAGE = "https://www.yoshkitobchi.uz/media/propaganda.png"


@router.message(F.text == "🗞 Targ‘ibot")
async def advert_handler(message: Message) -> None:
    """Handle the 'Targ‘ibot' button."""

    bot_username = (await bot.me()).username

    async with session_maker() as session:
        user_service = UserService(session)

        referral_link = await user_service.get_referral_link(
            user_id=message.from_user.id,
            username=bot_username,
        )

    share_text = (
        "📚 “Yosh Kitobchi — 2026 yoz” loyihasiga qo‘shiling!\n\n"
        "🏆 Kitobxonlik tanlovlari\n"
        "🔥 Eng faol targ‘ibotchilar uchun sovg‘alar\n"
        "📖 Bilimingizni sinab ko‘ring va reytingda yuqorilang.\n\n"
        f"🔗 {referral_link}"
    )

    share_url = (
        f"https://t.me/share/url?url={quote(referral_link)}&text={quote(share_text)}"
    )

    inline_share = f"https://t.me/{bot_username}?start={message.from_user.id}"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📤 Do‘stlarga ulashish",
                    switch_inline_query=inline_share,
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

    caption = f"""
🗞 <b>Targ‘ibot bo‘limi</b>

📚 “Yosh Kitobchi — 2026 yoz” loyihasiga
do‘stlaringizni taklif qiling.

🏆 Har bir ro‘yxatdan o‘tgan foydalanuvchi
uchun bonus ball beriladi.

🔗 <b>Sizning maxsus havolangiz:</b>

<code>{referral_link}</code>

🔥 Eng faol targ‘ibotchilar
loyiha yakunida taqdirlanadi.
"""

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
async def inline_share_handler(
    inline_query: InlineQuery,
) -> None:
    """
    Inline share system.
    """

    query = inline_query.query

    referral_link = "https://t.me/yoshkitobchibot"

    if query.startswith("https://t.me/"):
        referral_link = query

    text = (
        "📚 “Yosh Kitobchi — 2026 yoz” loyihasiga qo‘shiling!\n\n"
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

    await bot.answer_inline_query(
        inline_query.id,
        results=results,
        cache_time=1,
    )
