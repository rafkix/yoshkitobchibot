from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from app.filters.is_admin import IsAdmin
from app.keyboards.inline import admin_ads, admin_ads_send
from app.keyboards.reply import admin_menu
from data.config import ADMINS
from aiogram.fsm.context import FSMContext

from database.database import session_maker
from database.services.stats import StatService

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
        reply_markup=admin_menu(),
    )


# =========================
# STATISTICS
# =========================
@router.message(F.text == "📊 Statistika", IsAdmin(admin_ids=ADMINS))
async def admin_stats(message: Message):
    async with session_maker() as session:
        # Instantiate the service correctly
        service = StatService(session)

        total = await service.count_total_users()
        registered = await service.count_registered_users()
        unregistered = await service.count_unregistered_users()

        new_1d = await service.count_new_users_since(1)
        new_7d = await service.count_new_users_since(7)
        new_30d = await service.count_new_users_since(30)

        reg_1d = await service.count_new_registered_users_since(1)
        reg_7d = await service.count_new_registered_users_since(7)
        reg_30d = await service.count_new_registered_users_since(30)

    text = (
        "📊 <b>Statistika</b>\n"
        f"• Obunachilar soni: {total} ta\n"
        f"• Ro‘yxatdan o‘tganlar: {registered} ta\n"
        f"• Ro‘yxatdan o‘tmagan: {unregistered} ta\n\n"
        "📈 <b>Obunachilar qo‘shilishi</b>\n"
        f"• Oxirgi 24 soat: +{new_1d}\n"
        f"• Oxirgi 7 kun: +{new_7d}\n"
        f"• Oxirgi 30 kun: +{new_30d}\n\n"
        "📊 <b>Ro‘yxatdan o‘tish</b>\n"
        f"• 24 soat: {reg_1d}\n"
        f"• 7 kun: {reg_7d}\n"
        f"• 30 kun: {reg_30d}\n\n"
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
