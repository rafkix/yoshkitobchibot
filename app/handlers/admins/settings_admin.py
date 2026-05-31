# app/handlers/admins/settings_admin.py
"""
Bot umumiy sozlamalarini boshqarish:
- Ko'rish va o'zgartirish
- Targibot matni
- Test sozlamalari
- Referal ball
"""

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.filters.is_admin import IsAdmin
from app.keyboards.admin_flow import CANCEL_TEXT, cancel_reply_keyboard
from app.keyboards.reply import admin_menu
from data.config import ADMINS
from database.database import session_maker
from database.services.settings_service import SettingsService, DEFAULT_SETTINGS

router = Router()


# =========================================================
# STATES
# =========================================================


class SettingEditState(StatesGroup):
    waiting_value = State()


# =========================================================
# KEYBOARDS
# =========================================================

SETTINGS_LABELS = {
    "referral_score_per_user": "🎯 Referal ball (har bir referal uchun)",
    "test_max_questions": "📝 Test — maks. savollar soni",
    "test_seconds_per_question": "⏱ Test — savol vaqti (soniya)",
    "targibot_text": "🗞 Targ'ibot matni",
    "welcome_unregistered_text": "👋 Ro'yxatdan o'tmagan uchun xabar",
}


def settings_main_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for key, label in SETTINGS_LABELS.items():
        builder.button(text=f"✏️ {label}", callback_data=f"set_edit:{key}")
    builder.button(text="📋 Barchasini ko'rish", callback_data="set_view_all")
    builder.adjust(1)
    return builder.as_markup()


# =========================================================
# ENTRY
# =========================================================


@router.message(F.text == "⚙️ Sozlamalar", IsAdmin(admin_ids=ADMINS))
async def settings_admin_menu(message: Message):
    async with session_maker() as session:
        svc = SettingsService(session)
        ref_score = await svc.get_referral_score()
        max_q = await svc.get_int("test_max_questions", 40)
        sec_q = await svc.get_int("test_seconds_per_question", 90)

    await message.answer(
        "⚙️ <b>Bot sozlamalari</b>\n\n"
        f"🎯 Referal ball: <b>{ref_score}</b> ball/kishi\n"
        f"📝 Test savollar: <b>{max_q}</b> ta\n"
        f"⏱ Savol vaqti: <b>{sec_q} sek</b> ({sec_q // 60} daq)\n\n"
        "O'zgartirmoqchi bo'lgan sozlamani tanlang:",
        parse_mode="HTML",
        reply_markup=settings_main_keyboard(),
    )


# =========================================================
# VIEW ALL
# =========================================================


@router.callback_query(F.data == "set_view_all", IsAdmin(admin_ids=ADMINS))
async def set_view_all(callback: CallbackQuery):
    async with session_maker() as session:
        svc = SettingsService(session)
        all_settings = await svc.get_all()

    lines = ["⚙️ <b>Barcha sozlamalar</b>\n"]
    for s in all_settings:
        label = SETTINGS_LABELS.get(s.key, s.key)
        val = s.value[:80] + "..." if len(s.value) > 80 else s.value
        desc = s.description or ""
        lines.append(f"<b>{label}</b>\n  └ <code>{val}</code>")

    await callback.message.edit_text(
        "\n\n".join(lines),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⏪ Orqaga", callback_data="set_back")]
            ]
        ),
    )
    await callback.answer()


@router.callback_query(F.data == "set_back", IsAdmin(admin_ids=ADMINS))
async def set_back(callback: CallbackQuery):
    async with session_maker() as session:
        svc = SettingsService(session)
        ref_score = await svc.get_referral_score()
        max_q = await svc.get_int("test_max_questions", 40)
        sec_q = await svc.get_int("test_seconds_per_question", 90)

    await callback.message.edit_text(
        "⚙️ <b>Bot sozlamalari</b>\n\n"
        f"🎯 Referal ball: <b>{ref_score}</b> ball/kishi\n"
        f"📝 Test savollar: <b>{max_q}</b> ta\n"
        f"⏱ Savol vaqti: <b>{sec_q} sek</b> ({sec_q // 60} daq)\n\n"
        "O'zgartirmoqchi bo'lgan sozlamani tanlang:",
        parse_mode="HTML",
        reply_markup=settings_main_keyboard(),
    )
    await callback.answer()


# =========================================================
# EDIT SETTING
# =========================================================


@router.callback_query(F.data.startswith("set_edit:"), IsAdmin(admin_ids=ADMINS))
async def set_edit_start(callback: CallbackQuery, state: FSMContext):
    key = callback.data.split(":", 1)[1]
    if key not in SETTINGS_LABELS:
        return await callback.answer("❌ Noto'g'ri kalit", show_alert=True)

    async with session_maker() as session:
        current = await SettingsService(session).get(key)

    label = SETTINGS_LABELS[key]
    default_val, desc = DEFAULT_SETTINGS.get(key, (None, None))

    preview = current[:200] + "..." if current and len(current) > 200 else current

    await state.update_data(setting_key=key)
    await state.set_state(SettingEditState.waiting_value)

    hint = ""
    if key == "referral_score_per_user":
        hint = "\n\n💡 Raqam kiriting (masalan: 1, 2, 5)"
    elif key in ("test_max_questions", "test_seconds_per_question"):
        hint = "\n\n💡 Musbat raqam kiriting"
    elif "text" in key:
        hint = "\n\n💡 Matn kiriting. HTML formatda: <b>, <i>, <code> va boshqalar"

    await callback.message.answer(
        f"✏️ <b>{label}</b>\n\n"
        f"Hozirgi qiymat:\n<code>{preview or '—'}</code>\n\n"
        f"Yangi qiymatni kiriting:{hint}",
        parse_mode="HTML",
        reply_markup=cancel_reply_keyboard(),
    )
    await callback.answer()


@router.message(SettingEditState.waiting_value, IsAdmin(admin_ids=ADMINS))
async def set_edit_save(message: Message, state: FSMContext):
    if message.text in {"/cancel", CANCEL_TEXT}:
        await state.clear()
        return await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu())

    data = await state.get_data()
    key = data.get("setting_key")
    value = message.text.strip()

    # Validatsiya
    if key in (
        "referral_score_per_user",
        "test_max_questions",
        "test_seconds_per_question",
    ):
        if not value.isdigit() or int(value) < 1:
            return await message.answer("❌ Musbat raqam kiriting:")

    await state.clear()

    async with session_maker() as session:
        await SettingsService(session).set(key, value)

    label = SETTINGS_LABELS.get(key, key)
    preview = value[:100] + "..." if len(value) > 100 else value
    await message.answer(
        f"✅ <b>{label}</b> yangilandi!\n\nYangi qiymat: <code>{preview}</code>",
        parse_mode="HTML",
        reply_markup=admin_menu(),
    )
