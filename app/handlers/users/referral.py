# app/handlers/users/referral.py

from urllib.parse import quote
from aiogram.filters import Command

from aiogram import Bot, F, Router
from aiogram.types import InlineQuery, InlineQueryResultPhoto, Message

from app.keyboards.users.referral import inline_join_keyboard, referral_share_keyboard
from database.database import session_maker
from database.services.contest_service import ContestService
from database.services.referral_service import (
    ReferralService,
)  # ✅ ReferralService ishlatiladi
from database.services.user_service import UserService

router = Router()

PROMO_IMAGE = "https://www.yoshkitobchi.uz/media/propaganda.png"


@router.message(Command("propaganda"))
@router.message(F.text.in_({"🗞 Targ‘ibot", "🎁 Konkurs"}))
async def targibot_or_contest_handler(message: Message, bot: Bot) -> None:
    user_id = message.from_user.id

    bot_info = await bot.get_me()
    bot_username = bot_info.username

    async with session_maker() as session:
        u_service = UserService(session)
        r_service = ReferralService(session)  # ✅ ReferralService
        c_service = ContestService(session)

        # ✅ Barcha referral metodlar ReferralService orqali
        referral_link = await r_service.get_referral_link(user_id, bot_username)
        referrals_total = await r_service.get_referral_count(
            user_id, registered_only=False
        )
        referrals_registered = await r_service.get_referral_count(
            user_id, registered_only=True
        )
        active_contest = await c_service.get_active_contest()
        user = await u_service.get_user(user_id)
        user_ref_score = user.referral_score if user else 0

    share_text = '📚 "Yosh Kitobchi — 2026 yoz" loyihasiga qo\'shiling! 🏆'
    share_url = (
        f"https://t.me/share/url?url={quote(referral_link)}&text={quote(share_text)}"
    )
    keyboard = referral_share_keyboard(referral_link, share_url)

    if active_contest:
        if referrals_registered >= active_contest.min_referrals:
            status_line = (
                f"✅ <b>Siz shartni bajardingiz!</b> "
                f"({referrals_registered}/{active_contest.min_referrals})"
            )
        else:
            status_line = (
                f"⏳ Shart: {referrals_registered}/{active_contest.min_referrals} "
                "ta do‘st ro‘yxatdan o‘tishi kerak"
            )

        contest_body = active_contest.button_text or active_contest.description or ""

        caption = (
            f"🎉 <b>{active_contest.title}</b>\n\n"
            f"{contest_body}\n\n"
            f"🎁 <b>Sovg‘a:</b> {active_contest.prize_description or '—'}\n\n"
            f"📌 <b>Shart:</b> kamida <b>{active_contest.min_referrals}</b> ta "
            f"do‘stingiz ro‘yxatdan o‘tsin\n\n"
            f"{status_line}\n\n"
            f"👥 <b>Taklif qilganlar:</b> {referrals_total} ta\n"
            f"✅ <b>Ro‘yxatdan o‘tganlar:</b> {referrals_registered} ta\n\n"
            "🎲 Ko‘proq ro‘yxatdan o‘tgan referal imkoniyatingizni oshiradi, "
            "ammo shartni bajargan har bir ishtirokchi yutishi mumkin.\n\n"
            f"🔗 <b>Sizning havolangiz:</b>\n<code>{referral_link}</code>"
        )
    else:
        caption = (
            "🗞 <b>Targ‘ibot bo‘limi</b>\n\n"
            '"Yosh kitobchi" — 2026 yoz loyihasiga\n'
            "do‘stlaringizni taklif qiling.\n\n"
            f"👥 <b>Taklif qilganlar:</b> {referrals_total} ta\n"
            f"✅ <b>Ro‘yxatdan o‘tganlar:</b> {referrals_registered} ta\n"
            f"🎯 <b>Referal ballari:</b> {user_ref_score} ball\n\n"
            f"🔗 <b>Sizning maxsus havolangiz:</b>\n\n"
            f"<code>{referral_link}</code>\n\n"
            "🔥 Eng faol targ‘ibotchilar loyiha yakunida taqdirlanadi."
        )

    await message.answer_photo(
        photo=PROMO_IMAGE,
        caption=caption,
        parse_mode="HTML",
        reply_markup=keyboard,
    )


@router.inline_query()
async def inline_share_handler(inline_query: InlineQuery, bot: Bot) -> None:
    query = inline_query.query.strip()

    if query.startswith("https://t.me/"):
        referral_link = query
    elif query.isdigit():
        bot_info = await bot.get_me()
        referral_link = f"https://t.me/{bot_info.username}?start={query}"
    else:
        referral_link = "https://t.me/yoshkitobchibot"

    text = (
        '"Yosh kitobchi" — 2026 yoz loyihasiga qo\'shiling!\n\n'
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
            reply_markup=inline_join_keyboard(referral_link),
        )
    ]

    await inline_query.answer(results=results, cache_time=1)
