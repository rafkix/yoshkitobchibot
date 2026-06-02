from aiogram import F, Router
from aiogram.types import Message

from database.database import session_maker
from database.services.user_service import UserService

router = Router()

MEDALS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]


@router.message(F.text == "📊 Reyting")
async def rating_handler(message: Message) -> None:
    user_id = message.from_user.id

    async with session_maker() as session:
        service = UserService(session)
        user = await service.get_user(user_id)
        if not user:
            return await message.answer(
                "📄 Profil topilmadi. Iltimos, ro‘yxatdan o‘ting."
            )

        top_users = await service.get_top_users(limit=10)

        if user.is_registered:
            rank = await service.get_user_rank(user_id)
            user_rank_line = f"\n📊 <b>Siz:</b> #{rank} — {user.total_score} ball"
        else:
            user_rank_line = "\n⚠️ <i>Reytingda ko‘rinish uchun ro‘yxatdan o‘ting.</i>"

    lines = ["🏆 <b>Top 10 — Eng faol ishtirokchilar</b>\n"]
    for idx, u in enumerate(top_users):
        medal = MEDALS[idx] if idx < len(MEDALS) else f"{idx + 1}."
        name = u.full_name or f"Foydalanuvchi #{u.user_id}"
        lines.append(f"{medal}. {name} — {u.total_score} ball")

    lines.append(user_rank_line)
    await message.answer("\n".join(lines), parse_mode="HTML")
