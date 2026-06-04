# app/handlers/admin/main_admin.py

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from app.filters.is_admin import IsAdmin
from app.keyboards.inline import admin_ads, admin_ads_send
from app.keyboards.reply import admin_menu
from data.config import ADMINS

from database.database import session_maker
from database.services.stats import StatService

router = Router()

ADMIN_TEXT = "🔐 Admin panel\nKerakli bo‘limni tanlang."


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
        service = StatService(session)
        stats = await service.get_dashboard_stats()

    total = stats["total_users"]
    registered = stats["registered_users"]
    unregistered = stats["unregistered_users"]
    started_tests = stats["started_test_users"]
    completed_tests = stats["completed_test_users"]
    never_started = stats["never_started_test_users"]
    active_sessions = stats["active_test_sessions"]

    text = (
        "📊 <b>Loyiha statistikasi</b>\n\n"
        "👥 <b>Foydalanuvchilar</b>\n"
        f"• Jami: <b>{total}</b>\n"
        f"• Ro‘yxatdan o‘tgan: <b>{registered}</b>\n"
        f"• Ro‘yxatdan o‘tmagan: <b>{unregistered}</b>\n\n"
        "📈 <b>Yangi foydalanuvchilar</b>\n"
        f"• 24 soat: <b>+{stats['new_users_24h']}</b>\n"
        f"• Ro‘yxatdan o‘tganlar: <b>{stats['new_registered_24h']}</b>\n\n"
        "📝 <b>Test statistikasi</b>\n"
        f"• Test boshlaganlar: <b>{started_tests}</b>\n"
        f"• Test tugatganlar: <b>{completed_tests}</b>\n"
        f"• Test ishlamaganlar: <b>{never_started}</b>\n"
        f"• Aktiv sessiyalar: <b>{active_sessions}</b>\n\n"
        "⏱ <b>Oxirgi 24 soat</b>\n"
        f"• Test boshlaganlar: <b>{stats['new_test_users_24h']}</b>\n"
        f"• Test tugatganlar: <b>{stats['completed_test_users_24h']}</b>"
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
