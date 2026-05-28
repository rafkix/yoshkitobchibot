from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from app.filters.is_admin import IsAdmin
from app.keyboards.inline import admin_ads, admin_ads_send
from app.keyboards.reply import admin_menu
from data.config import ADMINS
from aiogram.fsm.context import FSMContext

from database.database import session_maker
from database.services.stats import count_active_users, count_active_users_since, count_left_users, count_new_users_since, count_total_users

router = Router()


ADMIN_TEXT = "🔐 Admin panel\nKerakli bo‘limni tanlang."

print(ADMINS)

# =========================
# PANEL
# =========================
@router.message(Command("panel"), IsAdmin(admin_ids=ADMINS))
async def admin_panel(message: Message):
    await message.answer(
        ADMIN_TEXT,
        reply_markup=admin_menu(),
    )


@router.message(F.text == "⬅️ Orqaga", IsAdmin(admin_ids=ADMINS))
async def back_to_management(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        ADMIN_TEXT,
        parse_mode="HTML",
        reply_markup=admin_menu(),  # sendagi asosiy reply keyboard
    )

# =========================
# STATISTICS
# =========================
@router.message(F.text == "📊 Statistika", IsAdmin(admin_ids=ADMINS))
async def admin_stats(message: Message):
    async with session_maker() as session:
        total = await count_total_users(session)
        active = await count_active_users(session)
        left = await count_left_users(session)

        new_1d = await count_new_users_since(session, 1)
        new_7d = await count_new_users_since(session, 7)
        new_30d = await count_new_users_since(session, 30)

        act_1d = await count_active_users_since(session, 1)
        act_7d = await count_active_users_since(session, 7)
        act_30d = await count_active_users_since(session, 30)


    text = (
        "📊 <b>Statistika</b>\n"
        f"• Obunachilar soni: {total} ta\n"
        f"• Faol obunachilar: {active} ta\n"
        f"• Tark etganlar: {left} ta\n\n"
        "📈 <b>Obunachilar qo‘shilishi</b>\n"
        f"• Oxirgi 24 soat: +{new_1d}\n"
        f"• Oxirgi 7 kun: +{new_7d}\n"
        f"• Oxirgi 30 kun: +{new_30d}\n\n"
        "📊 <b>Faollik</b>\n"
        f"• 24 soat: {act_1d}\n"
        f"• 7 kun: {act_7d}\n"
        f"• 30 kun: {act_30d}\n\n"
    )

    await message.answer(text, parse_mode="HTML", reply_markup=admin_menu())

# =========================
# ADS
# =========================
@router.message(F.text == "📢 Reklama", IsAdmin(admin_ids=ADMINS))
async def admin_ad(message: Message):
    await message.answer("📢 Reklama boshqaruvi:", reply_markup=admin_ads())


# =========================
# BROADCAST
# =========================
@router.message(F.text == "📨 Xabar yuborish", IsAdmin(admin_ids=ADMINS))
async def admin_broadcast(message: Message):
    await message.answer(
        "📨 Foydalanuvchilarga yuboradigan xabar turini tanlang.",
        reply_markup=admin_ads_send(),
    )