from aiogram.filters import Command
from aiogram import Router, F
from aiogram.types import Message, FSInputFile

router = Router()

PRIZES_PHOTO_PATH = "/home/ubuntu/apps/yoshkitobchibot/media/prizes.png"

PRIZES_TEXT = (
    "🏆 <b>YOSHKITOBCHI 2026 — Sovg‘alar</b>\n\n"
    "🥇 <b>1-o‘rin</b> — Planshet(Redmi Pad SE)\n"
    "🥈 <b>2-o‘rin</b> — 3 oylik Premium obuna\n"
    "🥉 <b>3-o‘rin</b> — 1 oylik Premium obuna\n"
    "🎖 <b>4-o‘rin</b> — Kitoblar to‘plami\n"
    "🎖 <b>5-o‘rin</b> — Kitoblar to‘plami\n\n"
    "✨ o‘qi, o‘rgan, yarat!\n"
    "yoshkitobchi.uz"
)

@router.message(Command("prizes"))
@router.message(F.text == "🎁 Sovg‘alar")
async def prizes_handler(message: Message):
    await message.answer_photo(
        photo=FSInputFile(PRIZES_PHOTO_PATH),
        caption=PRIZES_TEXT,
        parse_mode="HTML",
    )
