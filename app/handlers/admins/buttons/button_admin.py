# app/handlers/admins/buttons/button_admin.py
"""
Admin uchun tugmalar boshqaruvi:
- Yangi tugma qo'shish (URL, xabar, handler)
- Tugmalarni ko'rish va o'zgartirish
- Ro'yxatdan o'tmagan userlarga xabar yuborish
- Broadcast filter (registered/unregistered)
"""

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.filters.is_admin import IsAdmin
from app.keyboards.admin_flow import CANCEL_TEXT, cancel_reply_keyboard
from app.keyboards.reply import admin_menu
from data.config import ADMINS
from database.database import session_maker
from database.models import CustomButton
from database.services.settings_service import SettingsService
from database.services.user_service import UserService
from sqlalchemy import select

router = Router()


# =========================================================
# STATES
# =========================================================

class ButtonCreateState(StatesGroup):
    name = State()
    text = State()
    action_type = State()
    action_value = State()
    menu_section = State()


class BroadcastUnregisteredState(StatesGroup):
    waiting_message = State()


class ReferralScoreState(StatesGroup):
    waiting_score = State()


# =========================================================
# KEYBOARDS
# =========================================================

def buttons_main_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Yangi tugma qo'shish", callback_data="btn_create")
    builder.button(text="📋 Tugmalar ro'yxati", callback_data="btn_list")
    builder.button(text="📢 Ro'yxatdan o'tmaganlarga xabar", callback_data="btn_broadcast_unreg")
    builder.button(text="🎯 Referal ball sozlash", callback_data="btn_ref_score")
    builder.adjust(1)
    return builder.as_markup()


def action_type_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔗 URL havola", callback_data="btn_act:url")
    builder.button(text="💬 Xabar matni", callback_data="btn_act:message")
    builder.button(text="❌ Bekor qilish", callback_data="btn_cancel")
    builder.adjust(1)
    return builder.as_markup()


def buttons_list_keyboard(buttons: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for b in buttons:
        icon = "🟢" if b.is_active else "🔴"
        act = {"url": "🔗", "message": "💬"}.get(b.action_type, "❓")
        builder.button(
            text=f"{icon} {act} {b.text[:30]}",
            callback_data=f"btn_view:{b.id}",
        )
    builder.button(text="⏪ Orqaga", callback_data="btn_back_main")
    builder.adjust(1)
    return builder.as_markup()


def button_detail_keyboard(button) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if button.is_active:
        builder.button(text="🔴 O'chirish", callback_data=f"btn_toggle:{button.id}")
    else:
        builder.button(text="🟢 Yoqish", callback_data=f"btn_toggle:{button.id}")
    builder.button(text="🗑 O'chirish", callback_data=f"btn_delete:{button.id}")
    builder.button(text="⏪ Orqaga", callback_data="btn_list")
    builder.adjust(1)
    return builder.as_markup()


# =========================================================
# ENTRY
# =========================================================

@router.message(F.text == "🔘 Tugmalar", IsAdmin(admin_ids=ADMINS))
async def buttons_admin_menu(message: Message):
    await message.answer(
        "🔘 <b>Tugmalar boshqaruvi</b>\n\n"
        "Bu yerda botdagi tugmalarni sozlashingiz,\n"
        "foydalanuvchilarga xabar yuborishingiz mumkin.",
        parse_mode="HTML",
        reply_markup=buttons_main_keyboard(),
    )


@router.callback_query(F.data == "btn_back_main", IsAdmin(admin_ids=ADMINS))
async def btn_back_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "🔘 <b>Tugmalar boshqaruvi</b>",
        parse_mode="HTML",
        reply_markup=buttons_main_keyboard(),
    )
    await callback.answer()


# =========================================================
# TUGMA YARATISH
# =========================================================

@router.callback_query(F.data == "btn_create", IsAdmin(admin_ids=ADMINS))
async def btn_create_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ButtonCreateState.name)
    await callback.message.answer(
        "➕ <b>Yangi tugma yaratish</b>\n\n"
        "1️⃣ Tugma ichki nomini kiriting (admin uchun):\n"
        "Masalan: <i>Sayt havolasi</i>",
        parse_mode="HTML",
        reply_markup=cancel_reply_keyboard(),
    )
    await callback.answer()


@router.message(ButtonCreateState.name, IsAdmin(admin_ids=ADMINS))
async def btn_create_name(message: Message, state: FSMContext):
    if message.text in {"/cancel", CANCEL_TEXT}:
        await state.clear()
        return await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu())
    await state.update_data(name=message.text.strip())
    await state.set_state(ButtonCreateState.text)
    await message.answer(
        "2️⃣ Tugmada ko'rsatiladigan matnni kiriting:\n"
        "Masalan: <i>🌐 Saytga o'tish</i>",
        parse_mode="HTML",
        reply_markup=cancel_reply_keyboard(),
    )


@router.message(ButtonCreateState.text, IsAdmin(admin_ids=ADMINS))
async def btn_create_text(message: Message, state: FSMContext):
    if message.text in {"/cancel", CANCEL_TEXT}:
        await state.clear()
        return await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu())
    await state.update_data(text=message.text.strip())
    await state.set_state(ButtonCreateState.action_type)
    await message.answer(
        "3️⃣ Tugma turini tanlang:",
        reply_markup=action_type_keyboard(),
    )


@router.callback_query(F.data.startswith("btn_act:"), IsAdmin(admin_ids=ADMINS))
async def btn_create_action_type(callback: CallbackQuery, state: FSMContext):
    action_type = callback.data.split(":")[1]
    await state.update_data(action_type=action_type)
    await state.set_state(ButtonCreateState.action_value)

    if action_type == "url":
        prompt = (
            "4️⃣ URL manzilini kiriting:\n"
            "Masalan: <code>https://yoshkitobchi.uz</code>"
        )
    else:
        prompt = (
            "4️⃣ Foydalanuvchiga yuboriladigan xabar matnini kiriting:\n"
            "(HTML formatida yozsa bo'ladi)"
        )

    await callback.message.answer(
        prompt,
        parse_mode="HTML",
        reply_markup=cancel_reply_keyboard(),
    )
    await callback.answer()


@router.message(ButtonCreateState.action_value, IsAdmin(admin_ids=ADMINS))
async def btn_create_action_value(message: Message, state: FSMContext):
    if message.text in {"/cancel", CANCEL_TEXT}:
        await state.clear()
        return await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu())

    data = await state.get_data()
    await state.clear()

    async with session_maker() as session:
        button = CustomButton(
            name=data["name"],
            text=data["text"],
            action_type=data["action_type"],
            action_value=message.text.strip(),
            is_active=True,
            menu_section="main",
        )
        session.add(button)
        await session.commit()
        await session.refresh(button)

    act_label = {"url": "🔗 URL", "message": "💬 Xabar"}.get(data["action_type"], "❓")
    await message.answer(
        f"✅ <b>Tugma yaratildi!</b>\n\n"
        f"📌 Nom: {data['name']}\n"
        f"🔘 Matn: {data['text']}\n"
        f"⚡️ Tur: {act_label}\n"
        f"📎 Qiymat: {message.text[:50]}...",
        parse_mode="HTML",
        reply_markup=admin_menu(),
    )


@router.callback_query(F.data == "btn_cancel", IsAdmin(admin_ids=ADMINS))
async def btn_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Bekor qilindi.")
    await callback.answer()


# =========================================================
# TUGMALAR Ro'YXATI
# =========================================================

@router.callback_query(F.data == "btn_list", IsAdmin(admin_ids=ADMINS))
async def btn_list(callback: CallbackQuery):
    async with session_maker() as session:
        result = await session.execute(
            select(CustomButton).order_by(CustomButton.position, CustomButton.id)
        )
        buttons = result.scalars().all()

    if not buttons:
        await callback.message.edit_text(
            "📋 Hozircha tugma yo'q.\n\n➕ Yangisini qo'shing.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="➕ Yaratish", callback_data="btn_create"),
                InlineKeyboardButton(text="⏪ Orqaga", callback_data="btn_back_main"),
            ]])
        )
        return await callback.answer()

    await callback.message.edit_text(
        f"📋 <b>Tugmalar — {len(buttons)} ta</b>",
        parse_mode="HTML",
        reply_markup=buttons_list_keyboard(buttons),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("btn_view:"), IsAdmin(admin_ids=ADMINS))
async def btn_view(callback: CallbackQuery):
    button_id = int(callback.data.split(":")[1])
    async with session_maker() as session:
        result = await session.execute(
            select(CustomButton).where(CustomButton.id == button_id)
        )
        button = result.scalar_one_or_none()

    if not button:
        return await callback.answer("❌ Topilmadi", show_alert=True)

    act_label = {"url": "🔗 URL", "message": "💬 Xabar matni"}.get(button.action_type, "❓")
    status = "🟢 Aktiv" if button.is_active else "🔴 Faolsiz"
    text = (
        f"🔘 <b>{button.text}</b>\n\n"
        f"📌 Nom: {button.name}\n"
        f"📌 Holat: {status}\n"
        f"⚡️ Tur: {act_label}\n\n"
        f"📎 <b>Qiymat:</b>\n<code>{button.action_value or '—'}</code>\n\n"
        f"🗓 Yaratilgan: {button.created_at.strftime('%Y-%m-%d')}"
    )
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=button_detail_keyboard(button),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("btn_toggle:"), IsAdmin(admin_ids=ADMINS))
async def btn_toggle(callback: CallbackQuery):
    button_id = int(callback.data.split(":")[1])
    async with session_maker() as session:
        result = await session.execute(
            select(CustomButton).where(CustomButton.id == button_id)
        )
        button = result.scalar_one_or_none()
        if not button:
            return await callback.answer("❌ Topilmadi", show_alert=True)
        button.is_active = not button.is_active
        await session.commit()
        status = "🟢 Yoqildi" if button.is_active else "🔴 O'chirildi"

    await callback.answer(f"{status}!")
    await btn_view(callback)


@router.callback_query(F.data.startswith("btn_delete:"), IsAdmin(admin_ids=ADMINS))
async def btn_delete(callback: CallbackQuery):
    from sqlalchemy import delete as sql_delete
    button_id = int(callback.data.split(":")[1])
    async with session_maker() as session:
        await session.execute(
            sql_delete(CustomButton).where(CustomButton.id == button_id)
        )
        await session.commit()

    await callback.message.edit_text(
        "✅ Tugma o'chirildi.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⏪ Orqaga", callback_data="btn_list")
        ]])
    )
    await callback.answer("🗑 O'chirildi!")


# =========================================================
# Ro'YXATDAN O'TMAGANLARGA BROADCAST
# =========================================================

@router.callback_query(F.data == "btn_broadcast_unreg", IsAdmin(admin_ids=ADMINS))
async def btn_broadcast_unreg_start(callback: CallbackQuery, state: FSMContext):
    async with session_maker() as session:
        users = await UserService(session).get_all_users()
    unreg_count = sum(1 for u in users if not u.is_registered)

    await state.set_state(BroadcastUnregisteredState.waiting_message)
    await callback.message.answer(
        f"📢 <b>Ro'yxatdan o'tmaganlarga xabar</b>\n\n"
        f"👥 Maqsadli foydalanuvchilar: <b>{unreg_count} ta</b>\n\n"
        "Yuboriladigan xabar matnini yozing:\n"
        "(HTML format qo'llab-quvvatlanadi)",
        parse_mode="HTML",
        reply_markup=cancel_reply_keyboard(),
    )
    await callback.answer()


@router.message(BroadcastUnregisteredState.waiting_message, IsAdmin(admin_ids=ADMINS))
async def btn_broadcast_unreg_send(message: Message, state: FSMContext):
    if message.text in {"/cancel", CANCEL_TEXT}:
        await state.clear()
        return await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu())

    await state.clear()
    text = message.text

    async with session_maker() as session:
        users = await UserService(session).get_all_users()

    unreg_users = [u for u in users if not u.is_registered]
    total = len(unreg_users)

    status_msg = await message.answer(
        f"⏳ Yuborilmoqda... (0/{total})",
        parse_mode="HTML",
    )

    success, failed = 0, 0
    for i, user in enumerate(unreg_users):
        try:
            await message.bot.send_message(
                chat_id=user.user_id,
                text=text,
                parse_mode="HTML",
            )
            success += 1
        except Exception:
            failed += 1

        # Progress update har 20 ta da
        if (i + 1) % 20 == 0:
            try:
                await status_msg.edit_text(
                    f"⏳ Yuborilmoqda... ({i+1}/{total})"
                )
            except Exception:
                pass

    await status_msg.edit_text(
        f"✅ <b>Yuborish yakunlandi!</b>\n\n"
        f"👥 Jami: {total} ta\n"
        f"✅ Muvaffaqiyatli: {success} ta\n"
        f"❌ Bloklagan/xato: {failed} ta",
        parse_mode="HTML",
    )


# =========================================================
# REFERAL BALL SOZLASH
# =========================================================

@router.callback_query(F.data == "btn_ref_score", IsAdmin(admin_ids=ADMINS))
async def btn_ref_score_show(callback: CallbackQuery, state: FSMContext):
    async with session_maker() as session:
        current = await SettingsService(session).get_referral_score()

    await state.set_state(ReferralScoreState.waiting_score)
    await callback.message.answer(
        f"🎯 <b>Referal ball sozlash</b>\n\n"
        f"Hozirgi sozlama: <b>{current} ball</b> har bir ro'yxatdan o'tgan referal uchun\n\n"
        "Yangi qiymatni kiriting (1-100):",
        parse_mode="HTML",
        reply_markup=cancel_reply_keyboard(),
    )
    await callback.answer()


@router.message(ReferralScoreState.waiting_score, IsAdmin(admin_ids=ADMINS))
async def btn_ref_score_save(message: Message, state: FSMContext):
    if message.text in {"/cancel", CANCEL_TEXT}:
        await state.clear()
        return await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu())

    if not message.text.isdigit() or not (1 <= int(message.text) <= 100):
        return await message.answer("❌ 1 dan 100 gacha raqam kiriting:")

    await state.clear()
    async with session_maker() as session:
        await SettingsService(session).set_referral_score(int(message.text))

    await message.answer(
        f"✅ Referal ball <b>{message.text} ta</b> ga o'zgartirildi!\n\n"
        "Endi har bir yangi ro'yxatdan o'tgan referal uchun "
        f"<b>+{message.text} ball</b> beriladi.",
        parse_mode="HTML",
        reply_markup=admin_menu(),
    )
