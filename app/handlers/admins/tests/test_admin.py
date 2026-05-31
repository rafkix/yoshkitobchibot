# app/handlers/admins/tests/test_admin.py
"""
Admin uchun test boshqaruvi:
- Testlarni ko'rish, faollashtirish/o'chirish
- Test vaqti va savol sonini sozlash
- Test sessiyalarini ko'rish
"""

from datetime import datetime, UTC, timedelta

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, func

from app.filters.is_admin import IsAdmin
from app.keyboards.admin_flow import CANCEL_TEXT, cancel_reply_keyboard
from app.keyboards.reply import admin_menu
from data.config import ADMINS
from database.database import session_maker
from database.models import Test, Question, TestSession
from database.services.settings_service import SettingsService

router = Router()


# =========================================================
# STATES
# =========================================================

class TestSettingsState(StatesGroup):
    edit_max_questions = State()
    edit_seconds_per_question = State()


class TestTitleEditState(StatesGroup):
    waiting_new_title = State()


class TestScheduleState(StatesGroup):
    waiting_days = State()


# =========================================================
# KEYBOARDS
# =========================================================

def tests_admin_main_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Testlar ro'yxati", callback_data="ta_list")
    builder.button(text="⚙️ Test sozlamalari", callback_data="ta_settings")
    builder.button(text="📊 Statistika", callback_data="ta_stats")
    builder.adjust(1)
    return builder.as_markup()


def tests_list_admin_keyboard(tests: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for t in tests:
        icon = "🟢" if t.is_active else "🔴"
        q_label = ""
        builder.button(
            text=f"{icon} {t.title[:35]}",
            callback_data=f"ta_view:{t.id}",
        )
    builder.button(text="⏪ Orqaga", callback_data="ta_back_main")
    builder.adjust(1)
    return builder.as_markup()


def test_detail_keyboard(test) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if test.is_active:
        builder.button(text="🔴 Faolsizlashtirish", callback_data=f"ta_toggle:{test.id}")
    else:
        builder.button(text="🟢 Faollashtirish", callback_data=f"ta_toggle:{test.id}")
    builder.button(text="🗓 1 kunlik test", callback_data=f"ta_schedule:{test.id}:1")
    builder.button(text="🗓 10 kunlik test", callback_data=f"ta_schedule:{test.id}:10")
    builder.button(text="⏱ Kun kiritish", callback_data=f"ta_schedule_custom:{test.id}")
    builder.button(text="♾ Doimiy ochiq", callback_data=f"ta_schedule_clear:{test.id}")
    builder.button(text="🗑 Sessiyalarni tozalash", callback_data=f"ta_clear_sessions:{test.id}")
    builder.button(text="⏪ Orqaga", callback_data="ta_list")
    builder.adjust(1)
    return builder.as_markup()


def test_settings_keyboard(max_q: int, sec_per_q: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=f"📝 Maks. savollar: {max_q} ta",
        callback_data="ta_edit_max_q",
    )
    builder.button(
        text=f"⏱ Har savol vaqti: {sec_per_q} sek ({sec_per_q//60} daq)",
        callback_data="ta_edit_sec_q",
    )
    builder.button(text="⏪ Orqaga", callback_data="ta_back_main")
    builder.adjust(1)
    return builder.as_markup()


def confirm_clear_keyboard(test_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Ha, tozalash", callback_data=f"ta_clear_confirm:{test_id}")
    builder.button(text="❌ Yo'q", callback_data=f"ta_view:{test_id}")
    builder.adjust(2)
    return builder.as_markup()


def format_window(test) -> str:
    if not test.starts_at and not test.ends_at:
        return "Doimiy ochiq"
    started = test.starts_at.strftime("%Y-%m-%d %H:%M") if test.starts_at else "—"
    ended = test.ends_at.strftime("%Y-%m-%d %H:%M") if test.ends_at else "—"
    return f"{started} → {ended}"


# =========================================================
# ENTRY
# =========================================================

@router.message(F.text == "📋 Testlar ro'yxati", IsAdmin(admin_ids=ADMINS))
async def admin_tests_menu(message: Message):
    await message.answer(
        "📋 <b>Testlar boshqaruvi</b>\n\n"
        "Bu yerda barcha testlarni ko'rishingiz, faollashtirish,\n"
        "o'chirish va sozlamalarni o'zgartira olasiz.",
        parse_mode="HTML",
        reply_markup=tests_admin_main_keyboard(),
    )


@router.callback_query(F.data == "ta_back_main", IsAdmin(admin_ids=ADMINS))
async def ta_back_main(callback: CallbackQuery):
    await callback.message.edit_text(
        "📋 <b>Testlar boshqaruvi</b>",
        parse_mode="HTML",
        reply_markup=tests_admin_main_keyboard(),
    )
    await callback.answer()


# =========================================================
# TESTLAR Ro'YXATI
# =========================================================

@router.callback_query(F.data == "ta_list", IsAdmin(admin_ids=ADMINS))
async def ta_list(callback: CallbackQuery):
    async with session_maker() as session:
        result = await session.execute(select(Test).order_by(Test.id))
        tests = result.scalars().all()

        # Har bir test uchun savol sonini olamiz
        test_q_counts = {}
        for t in tests:
            count = await session.scalar(
                select(func.count(Question.id)).where(
                    Question.test_id == t.id,
                    Question.is_active.is_(True),
                )
            )
            test_q_counts[t.id] = count or 0

    if not tests:
        await callback.message.edit_text(
            "📋 Hozircha test mavjud emas.\n\n"
            "Pastdagi tugma orqali avval test yarating yoki savol yuklang.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="➕ Test yaratish", callback_data="admin:create_test"),
                InlineKeyboardButton(text="⏪ Orqaga", callback_data="ta_back_main")
            ]])
        )
        return await callback.answer()

    lines = ["📋 <b>Barcha testlar</b>\n"]
    for t in tests:
        icon = "🟢" if t.is_active else "🔴"
        lines.append(f"{icon} <b>{t.title}</b> — {test_q_counts[t.id]} savol")

    await callback.message.edit_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=tests_list_admin_keyboard(tests),
    )
    await callback.answer()


# =========================================================
# TEST DETAIL
# =========================================================

@router.callback_query(F.data.startswith("ta_view:"), IsAdmin(admin_ids=ADMINS))
async def ta_view(callback: CallbackQuery):
    test_id = int(callback.data.split(":")[1])
    async with session_maker() as session:
        result = await session.execute(select(Test).where(Test.id == test_id))
        test = result.scalar_one_or_none()
        if not test:
            return await callback.answer("❌ Test topilmadi", show_alert=True)

        q_count = await session.scalar(
            select(func.count(Question.id)).where(
                Question.test_id == test_id,
                Question.is_active.is_(True),
            )
        )
        session_count = await session.scalar(
            select(func.count(TestSession.id)).where(TestSession.test_id == test_id)
        )
        completed_count = await session.scalar(
            select(func.count(TestSession.id)).where(
                TestSession.test_id == test_id,
                TestSession.is_completed.is_(True),
            )
        )

    status = "🟢 Aktiv" if test.is_active else "🔴 Faolsiz"
    text = (
        f"📋 <b>{test.title}</b>\n\n"
        f"📌 Holat: {status}\n"
        f"🗓 Ochilish oynasi: <b>{format_window(test)}</b>\n"
        f"❓ Savollar: <b>{q_count}</b> ta\n\n"
        f"📊 <b>Sessiyalar:</b>\n"
        f"  Jami: {session_count} ta\n"
        f"  ✅ Tugatilgan: {completed_count} ta\n"
        f"  ⏳ Davom etayotgan: {session_count - completed_count} ta\n\n"
        f"🗓 Yaratilgan: {test.created_at.strftime('%Y-%m-%d')}"
    )
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=test_detail_keyboard(test),
    )
    await callback.answer()


# =========================================================
# TOGGLE ACTIVE
# =========================================================

@router.callback_query(F.data.startswith("ta_toggle:"), IsAdmin(admin_ids=ADMINS))
async def ta_toggle(callback: CallbackQuery):
    test_id = int(callback.data.split(":")[1])
    async with session_maker() as session:
        result = await session.execute(select(Test).where(Test.id == test_id))
        test = result.scalar_one_or_none()
        if not test:
            return await callback.answer("❌ Topilmadi", show_alert=True)
        test.is_active = not test.is_active
        await session.commit()
        status = "🟢 Faollashtirildi" if test.is_active else "🔴 Faolsizlashtirildi"

    await callback.answer(f"{status}!")
    await ta_view(callback)


# =========================================================
# TEST VAQT OYNASI
# =========================================================

@router.callback_query(F.data.startswith("ta_schedule:"), IsAdmin(admin_ids=ADMINS))
async def ta_schedule(callback: CallbackQuery):
    _, test_id_raw, days_raw = callback.data.split(":")
    test_id = int(test_id_raw)
    days = int(days_raw)
    now = datetime.now(UTC)

    async with session_maker() as session:
        result = await session.execute(select(Test).where(Test.id == test_id))
        test = result.scalar_one_or_none()
        if not test:
            return await callback.answer("❌ Test topilmadi", show_alert=True)

        test.is_active = True
        test.starts_at = now
        test.ends_at = now + timedelta(days=days)
        await session.commit()

    await callback.answer(f"✅ Test {days} kunga aktiv qilindi!")
    await ta_view(callback)


@router.callback_query(F.data.startswith("ta_schedule_custom:"), IsAdmin(admin_ids=ADMINS))
async def ta_schedule_custom(callback: CallbackQuery, state: FSMContext):
    test_id = int(callback.data.split(":")[1])
    await state.update_data(schedule_test_id=test_id)
    await state.set_state(TestScheduleState.waiting_days)
    await callback.message.answer(
        "⏱ <b>Test necha kun aktiv bo'lsin?</b>\n\n"
        "Masalan: <b>1</b>, <b>10</b>, <b>30</b>",
        parse_mode="HTML",
        reply_markup=cancel_reply_keyboard(),
    )
    await callback.answer()


@router.message(TestScheduleState.waiting_days, IsAdmin(admin_ids=ADMINS))
async def ta_schedule_custom_save(message: Message, state: FSMContext):
    if message.text in {"/cancel", CANCEL_TEXT}:
        await state.clear()
        return await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu())
    if not message.text.isdigit() or int(message.text) < 1:
        return await message.answer("❌ Kamida 1 kun bo'lishi kerak.")

    days = int(message.text)
    data = await state.get_data()
    test_id = data["schedule_test_id"]
    now = datetime.now(UTC)
    await state.clear()

    async with session_maker() as session:
        result = await session.execute(select(Test).where(Test.id == test_id))
        test = result.scalar_one_or_none()
        if not test:
            return await message.answer("❌ Test topilmadi.", reply_markup=admin_menu())

        test.is_active = True
        test.starts_at = now
        test.ends_at = now + timedelta(days=days)
        await session.commit()

    await message.answer(
        f"✅ Test <b>{days} kun</b> davomida aktiv qilindi.",
        parse_mode="HTML",
        reply_markup=admin_menu(),
    )


@router.callback_query(F.data.startswith("ta_schedule_clear:"), IsAdmin(admin_ids=ADMINS))
async def ta_schedule_clear(callback: CallbackQuery):
    test_id = int(callback.data.split(":")[1])
    async with session_maker() as session:
        result = await session.execute(select(Test).where(Test.id == test_id))
        test = result.scalar_one_or_none()
        if not test:
            return await callback.answer("❌ Test topilmadi", show_alert=True)

        test.is_active = True
        test.starts_at = None
        test.ends_at = None
        await session.commit()

    await callback.answer("✅ Test doimiy ochiq qilindi!")
    await ta_view(callback)


# =========================================================
# SESSIYALARNI TOZALASH
# =========================================================

@router.callback_query(F.data.startswith("ta_clear_sessions:"), IsAdmin(admin_ids=ADMINS))
async def ta_clear_sessions(callback: CallbackQuery):
    test_id = int(callback.data.split(":")[1])
    await callback.message.edit_text(
        "⚠️ <b>Diqqat!</b>\n\n"
        "Bu test uchun barcha sessiyalar o'chiriladi.\n"
        "Foydalanuvchilar testni qayta topshira oladi.\n\n"
        "Davom etasizmi?",
        parse_mode="HTML",
        reply_markup=confirm_clear_keyboard(test_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ta_clear_confirm:"), IsAdmin(admin_ids=ADMINS))
async def ta_clear_confirm(callback: CallbackQuery):
    from sqlalchemy import delete
    test_id = int(callback.data.split(":")[1])
    async with session_maker() as session:
        await session.execute(
            delete(TestSession).where(TestSession.test_id == test_id)
        )
        await session.commit()

    await callback.message.edit_text(
        "✅ Sessiyalar tozalandi!\n\n"
        "Endi foydalanuvchilar bu testni qayta topshira oladi.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⏪ Testga qaytish", callback_data=f"ta_view:{test_id}")
        ]])
    )
    await callback.answer("✅ Tozalandi!")


# =========================================================
# TEST SOZLAMALARI
# =========================================================

@router.callback_query(F.data == "ta_settings", IsAdmin(admin_ids=ADMINS))
async def ta_settings(callback: CallbackQuery):
    async with session_maker() as session:
        svc = SettingsService(session)
        max_q = await svc.get_int("test_max_questions", 40)
        sec_q = await svc.get_int("test_seconds_per_question", 90)

    total_minutes = (max_q * sec_q) // 60
    await callback.message.edit_text(
        f"⚙️ <b>Test sozlamalari</b>\n\n"
        f"📝 Maksimal savollar soni: <b>{max_q} ta</b>\n"
        f"⏱ Har bir savol uchun vaqt: <b>{sec_q} sek ({sec_q//60} daq {sec_q%60} sek)</b>\n\n"
        f"📊 Umumiy test vaqti: <b>≈ {total_minutes} daqiqa</b>\n\n"
        "Tugmaga bosib o'zgartiring:",
        parse_mode="HTML",
        reply_markup=test_settings_keyboard(max_q, sec_q),
    )
    await callback.answer()


@router.callback_query(F.data == "ta_edit_max_q", IsAdmin(admin_ids=ADMINS))
async def ta_edit_max_q(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TestSettingsState.edit_max_questions)
    await callback.message.answer(
        "📝 <b>Maksimal savollar sonini kiriting</b>\n\n"
        "Masalan: <b>30</b>, <b>40</b>, <b>50</b>",
        parse_mode="HTML",
        reply_markup=cancel_reply_keyboard(),
    )
    await callback.answer()


@router.message(TestSettingsState.edit_max_questions, IsAdmin(admin_ids=ADMINS))
async def ta_save_max_q(message: Message, state: FSMContext):
    if message.text in {"/cancel", CANCEL_TEXT}:
        await state.clear()
        return await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu())
    if not message.text.isdigit() or int(message.text) < 5:
        return await message.answer("❌ Kamida 5 ta bo'lishi kerak. Qayta kiriting:")
    await state.clear()
    async with session_maker() as session:
        await SettingsService(session).set("test_max_questions", message.text)
    await message.answer(
        f"✅ Maksimal savollar soni <b>{message.text} ta</b> ga o'zgartirildi!",
        parse_mode="HTML",
        reply_markup=admin_menu(),
    )


@router.callback_query(F.data == "ta_edit_sec_q", IsAdmin(admin_ids=ADMINS))
async def ta_edit_sec_q(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TestSettingsState.edit_seconds_per_question)
    await callback.message.answer(
        "⏱ <b>Har bir savol uchun vaqtni kiriting (soniyada)</b>\n\n"
        "Masalan:\n"
        "• <b>60</b> = 1 daqiqa\n"
        "• <b>90</b> = 1.5 daqiqa\n"
        "• <b>120</b> = 2 daqiqa",
        parse_mode="HTML",
        reply_markup=cancel_reply_keyboard(),
    )
    await callback.answer()


@router.message(TestSettingsState.edit_seconds_per_question, IsAdmin(admin_ids=ADMINS))
async def ta_save_sec_q(message: Message, state: FSMContext):
    if message.text in {"/cancel", CANCEL_TEXT}:
        await state.clear()
        return await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu())
    if not message.text.isdigit() or int(message.text) < 30:
        return await message.answer("❌ Kamida 30 soniya bo'lishi kerak:")
    await state.clear()
    async with session_maker() as session:
        await SettingsService(session).set("test_seconds_per_question", message.text)
    val = int(message.text)
    await message.answer(
        f"✅ Har bir savol vaqti <b>{val} sek ({val//60} daq {val%60} sek)</b> ga o'zgartirildi!",
        parse_mode="HTML",
        reply_markup=admin_menu(),
    )


# =========================================================
# STATISTIKA
# =========================================================

@router.callback_query(F.data == "ta_stats", IsAdmin(admin_ids=ADMINS))
async def ta_stats(callback: CallbackQuery):
    async with session_maker() as session:
        total_tests = await session.scalar(select(func.count(Test.id)))
        active_tests = await session.scalar(
            select(func.count(Test.id)).where(Test.is_active.is_(True))
        )
        total_sessions = await session.scalar(select(func.count(TestSession.id)))
        completed_sessions = await session.scalar(
            select(func.count(TestSession.id)).where(TestSession.is_completed.is_(True))
        )
        total_questions = await session.scalar(
            select(func.count(Question.id)).where(Question.is_active.is_(True))
        )

    text = (
        "📊 <b>Test statistikasi</b>\n\n"
        f"📋 Jami testlar: <b>{total_tests}</b> ta\n"
        f"  🟢 Aktiv: <b>{active_tests}</b> ta\n"
        f"  🔴 Faolsiz: <b>{total_tests - active_tests}</b> ta\n\n"
        f"❓ Faol savollar: <b>{total_questions}</b> ta\n\n"
        f"📝 Jami sessiyalar: <b>{total_sessions}</b> ta\n"
        f"  ✅ Tugatilgan: <b>{completed_sessions}</b> ta\n"
        f"  ⏳ Davom etayotgan: <b>{total_sessions - completed_sessions}</b> ta"
    )
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⏪ Orqaga", callback_data="ta_back_main")
        ]])
    )
    await callback.answer()
