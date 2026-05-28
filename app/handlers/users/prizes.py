from aiogram import Router, F
from aiogram.types import Message

router = Router()

PRIZES_PHOTO_URL = "https://www.yoshkitobchi.uz/media/prizes.png"  # <- rasmni shu yerga qo'ying

PRIZES_TEXT = (
    "🏆 <b>YOSHKITOBCHI 2026 — Sovg‘alar</b>\n\n"
    "🥇 <b>1-o'rin</b> — Planshet\n"
    "🥈 <b>2-o'rin</b> — 6 oylik Premium obuna\n"
    "🥉 <b>3-o'rin</b> — 3 oylik Premium obuna\n"
    "🎖 <b>4-o'rin</b> — 1 oylik Premium obuna\n"
    "🎖 <b>5-o'rin</b> — 1 oylik Premium obuna\n\n"
    "✨ O'qi, o'rgan, yarat!\n"
    "yoshkitobchi.uz"
)


@router.message(F.text == "🎁 Sovg‘alar")
async def prizes_handler(message: Message):
    await message.answer_photo(
        photo=PRIZES_PHOTO_URL,
        caption=PRIZES_TEXT,
        parse_mode="HTML",
    )