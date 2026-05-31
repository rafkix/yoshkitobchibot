from urllib.parse import quote

from aiogram import F, Router
from aiogram.types import InlineQuery, InlineQueryResultPhoto, Message

from app.keyboards.users.referral import inline_join_keyboard, referral_share_keyboard
from database.database import session_maker
from database.services.contest_service import ContestService
from database.services.settings_service import SettingsService
from database.services.user_service import UserService
from main import bot

router = Router()

PROMO_IMAGE = "https://www.yoshkitobchi.uz/media/propaganda.png"


@router.message(F.text.in_({"🗞 Targ'ibot", "🗞 Targ‘ibot", "🎁 Konkurs"}))
async def targibot_or_contest_handler(message: Message) -> None:
    user_id = message.from_user.id
    bot_username = (await bot.me()).username

    async with session_maker() as session:
        u_service = UserService(session)
        c_service = ContestService(session)
        s_service = SettingsService(session)

        referral_link = await u_service.get_referral_link(user_id, bot_username)
        referrals_total = await u_service.get_referrals_count(user_id)
        referrals_registered = await u_service.get_registered_referrals_count(user_id)
        active_contest = await c_service.get_active_contest()
        ref_score_per_user = await s_service.get_referral_score()
        user = await u_service.get_user(user_id)
        user_ref_score = user.referral_score if user else 0

    share_text = "📚 \"Yosh Kitobchi — 2026 yoz\" loyihasiga qo'shiling! 🏆"
    share_url = (
        f"https://t.me/share/url?url={quote(referral_link)}"
        f"&text={quote(share_text)}"
    )
    keyboard = referral_share_keyboard(referral_link, share_url)

    if active_contest:
        status_line = (
            f"✅ <b>Siz shartni bajardingiz!</b> "
            f"({referrals_registered}/{active_contest.min_referrals})"
            if referrals_registered >= active_contest.min_referrals
            else (
                f"⏳ Shart: {referrals_registered}/{active_contest.min_referrals} "
                "ta do'st ro'yxatdan o'tishi kerak"
            )
        )
        contest_body = active_contest.button_text or active_contest.description or ""

        caption = (
            f"🎉 <b>{active_contest.title}</b>\n\n"
            f"{contest_body}\n\n"
            f"🎁 <b>Sovg'a:</b> {active_contest.prize_description or '—'}\n\n"
            f"📌 <b>Shart:</b> kamida <b>{active_contest.min_referrals}</b> ta "
            f"do'stingiz ro'yxatdan o'tsin\n\n"
            f"{status_line}\n\n"
            f"👥 <b>Taklif qilganlar:</b> {referrals_total} ta\n"
            f"✅ <b>Ro'yxatdan o'tganlar:</b> {referrals_registered} ta\n\n"
            "🎲 Ko'proq ro'yxatdan o'tgan referal imkoniyatingizni oshiradi, "
            "ammo shartni bajargan har bir ishtirokchi yutishi mumkin.\n\n"
            f"🔗 <b>Sizning havolangiz:</b>\n<code>{referral_link}</code>"
        )
    else:
        caption = (
            "🗞 <b>Targ'ibot bo'limi</b>\n\n"
            '"Yosh kitobchi" - 2026 yoz loyihasiga\n'
            "do'stlaringizni taklif qiling.\n\n"
            f"🏆 <b>Har bir ro'yxatdan o'tgan do'st</b>\n"
            f"   uchun <b>+{ref_score_per_user} ball</b> beriladi.\n\n"
            f"👥 <b>Taklif qilganlar:</b> {referrals_total} ta\n"
            f"✅ <b>Ro'yxatdan o'tganlar:</b> {referrals_registered} ta\n"
            f"🎯 <b>Referal ballari:</b> {user_ref_score} ball\n\n"
            f"🔗 <b>Sizning maxsus havolangiz:</b>\n\n"
            f"<code>{referral_link}</code>\n\n"
            "🔥 Eng faol targ'ibotchilar loyiha yakunida taqdirlanadi."
        )

    await message.answer_photo(
        photo=PROMO_IMAGE,
        caption=caption,
        parse_mode="HTML",
        reply_markup=keyboard,
    )


@router.inline_query()
async def inline_share_handler(inline_query: InlineQuery) -> None:
    query = inline_query.query
    referral_link = "https://t.me/yoshkitobchibot"

    if query.startswith("https://t.me/"):
        referral_link = query

    text = (
        '"Yosh kitobchi" - 2026 yoz loyihasiga qo\'shiling!\n\n'
        "🏆 Kitobxonlik tanlovlari\n"
        "🔥 Eng faol targ'ibotchilar uchun sovg'alar\n"
        "📖 Bilimingizni sinab ko'ring va reytingda yuqorilang.\n\n"
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

    await bot.answer_inline_query(inline_query.id, results=results, cache_time=1)
