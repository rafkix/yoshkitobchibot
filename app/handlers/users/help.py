from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

router = Router()

HELP_TEXT = """📋 <b>Yordam bo‘limi</b>

<b>Asosiy buyruqlar:</b>
/start — Botni ishga tushirish yoki menyuga qaytish
/help — Ushbu yordam xabari

<b>Menyu tugmalari:</b>

📄 <b>Test</b>
Bilimingizni sinab ko‘rish uchun testlar. To‘g‘ri javoblar uchun ball beriladi.

📊 <b>Reyting</b>
Barcha ishtirokchilar orasidagi o‘rningizni va top 10 foydalanuvchilarni ko‘ring.

👤 <b>Profil</b>
Shaxsiy ma'lumotlaringiz: ism, yashash joyi, telefon, tanlov va umumiy ballingiz.

🗞 <b>Targ‘ibot</b>
Do‘stlaringizni taklif qiling. Har bir ro‘yxatdan o‘tgan do‘st uchun bonus ball olasiz.

<b>Ro‘yxatdan o‘tish:</b>
Botdan to‘liq foydalanish uchun bir marta ro‘yxatdan o‘tish talab etiladi. Buning uchun /start bosing va ko‘rsatmalarga amal qiling.

<b>Muammo yuzaga keldimi?</b>
@yoshkitobchi_admin ga murojaat qiling."""


@router.message(Command("help"))
@router.message(F.text == "❓ Yordam")
async def help_handler(message: Message):
    await message.answer(HELP_TEXT, parse_mode="HTML")
