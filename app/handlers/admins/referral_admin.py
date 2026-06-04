# app/handlers/admin/referral_admin.py

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from app.filters.is_admin import IsAdmin
from app.keyboards.reply import admin_menu
from app.states.admin_referral import AdminReferralState
from data.config import ADMINS
from database.database import session_maker
from database.services.referral_service import ReferralService
from database.services.user_service import UserService

router = Router()

PAGE_SIZE = 10  # Bir sahifada nechta yozuv


# =========================================================
# KEYBOARDS
# =========================================================


def referral_admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👥 Referrallar ro‘yxati",
                    callback_data="ref_admin:list:0",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🏆 Top referrerlar",
                    callback_data="ref_admin:top",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Foydalanuvchi ballini o‘zgartirish",
                    callback_data="ref_admin:edit_score",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Barcha ballarni qayta hisoblash",
                    callback_data="ref_admin:recalc_all",
                ),
            ],
        ]
    )


def pagination_keyboard(page: int, total: int, prefix: str) -> InlineKeyboardMarkup:
    buttons = []
    row = []

    if page > 0:
        row.append(
            InlineKeyboardButton(
                text="⬅️ Oldingi",
                callback_data=f"{prefix}:{page - 1}",
            )
        )

    if (page + 1) * PAGE_SIZE < total:
        row.append(
            InlineKeyboardButton(
                text="Keyingi ➡️",
                callback_data=f"{prefix}:{page + 1}",
            )
        )

    if row:
        buttons.append(row)

    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 Menyuga qaytish",
                callback_data="ref_admin:menu",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_recalc_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Ha, qayta hisoblash",
                    callback_data="ref_admin:recalc_confirm",
                ),
                InlineKeyboardButton(
                    text="❌ Bekor qilish",
                    callback_data="ref_admin:menu",
                ),
            ]
        ]
    )


def back_to_ref_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔙 Menyuga qaytish",
                    callback_data="ref_admin:menu",
                )
            ]
        ]
    )


# =========================================================
# ENTRY POINT — tugma orqali
# =========================================================


@router.message(F.text == "🔗 Referral boshqaruv", IsAdmin(admin_ids=ADMINS))
async def referral_admin_entry(message: Message):
    await message.answer(
        "🔗 <b>Referral boshqaruv paneli</b>\n\nKerakli amalni tanlang:",
        parse_mode="HTML",
        reply_markup=referral_admin_menu(),
    )


# =========================================================
# MENU (inline orqali qaytish)
# =========================================================


@router.callback_query(F.data == "ref_admin:menu", IsAdmin(admin_ids=ADMINS))
async def back_to_ref_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "🔗 <b>Referral boshqaruv paneli</b>\n\nKerakli amalni tanlang:",
        parse_mode="HTML",
        reply_markup=referral_admin_menu(),
    )
    await callback.answer()


# =========================================================
# REFERRALLAR Ro‘YXATI (sahifalangan)
# =========================================================


@router.callback_query(F.data.startswith("ref_admin:list:"), IsAdmin(admin_ids=ADMINS))
async def referral_list(callback: CallbackQuery):
    page = int(callback.data.split(":")[-1])

    async with session_maker() as session:
        r_service = ReferralService(session)
        u_service = UserService(session)

        # Barcha referrer userlarni top referrerlar orqali olamiz
        top = await r_service.get_top_referrers(limit=1000)

    total = len(top)

    if total == 0:
        await callback.message.edit_text(
            "👥 Hozircha hech kim hech kimni taklif qilmagan.",
            reply_markup=back_to_ref_menu_keyboard(),
        )
        return await callback.answer()

    start = page * PAGE_SIZE
    end = min(start + PAGE_SIZE, total)
    page_items = top[start:end]

    lines = [f"👥 <b>Referrallar ro‘yxati</b> (jami: {total})\n"]

    for i, (user, ref_count) in enumerate(page_items, start=start + 1):
        name = user.full_name or f"ID: {user.user_id}"
        lines.append(
            f"{i}. <b>{name}</b>\n"
            f"   🆔 <code>{user.user_id}</code> | "
            f"👥 {ref_count} ta | "
            f"⭐ {user.referral_score} ball"
        )

    text = "\n".join(lines)
    keyboard = pagination_keyboard(page, total, "ref_admin:list")

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


# =========================================================
# TOP REFERRERLAR LEADERBOARD
# =========================================================


@router.callback_query(F.data == "ref_admin:top", IsAdmin(admin_ids=ADMINS))
async def referral_top(callback: CallbackQuery):
    async with session_maker() as session:
        r_service = ReferralService(session)
        top = await r_service.get_top_referrers(limit=20)

    if not top:
        await callback.message.edit_text(
            "🏆 Hozircha hech kim hech kimni taklif qilmagan.",
            reply_markup=back_to_ref_menu_keyboard(),
        )
        return await callback.answer()

    medals = ["🥇", "🥈", "🥉"]
    lines = ["🏆 <b>Top 20 referrerlar</b>\n"]

    for i, (user, ref_count) in enumerate(top):
        medal = medals[i] if i < 3 else f"{i + 1}."
        name = user.full_name or f"ID: {user.user_id}"
        lines.append(
            f"{medal} <b>{name}</b>\n"
            f"   👥 {ref_count} ta referal | ⭐ {user.referral_score} ball"
        )

    text = "\n".join(lines)
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=back_to_ref_menu_keyboard(),
    )
    await callback.answer()


# =========================================================
# BALLARNI Qo‘LDA o‘ZGARTIRISH
# =========================================================


@router.callback_query(F.data == "ref_admin:edit_score", IsAdmin(admin_ids=ADMINS))
async def edit_score_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminReferralState.waiting_user_id)
    await callback.message.edit_text(
        "✏️ <b>Foydalanuvchi ID sini kiriting:</b>\n\n"
        "<i>Telegram User ID raqamini yuboring.</i>",
        parse_mode="HTML",
        reply_markup=back_to_ref_menu_keyboard(),
    )
    await callback.answer()


@router.message(AdminReferralState.waiting_user_id, IsAdmin(admin_ids=ADMINS))
async def edit_score_get_user_id(message: Message, state: FSMContext):
    text = (message.text or "").strip()

    if not text.isdigit():
        return await message.answer(
            "❌ <b>Faqat raqam kiriting.</b>\n<i>Telegram User ID raqami bo‘lishi kerak.</i>",
            parse_mode="HTML",
        )

    user_id = int(text)

    async with session_maker() as session:
        u_service = UserService(session)
        user = await u_service.get_user(user_id)

    if not user:
        return await message.answer(
            f"❌ <b>ID {user_id} bo‘lgan foydalanuvchi topilmadi.</b>",
            parse_mode="HTML",
        )

    await state.update_data(target_user_id=user_id)
    await state.set_state(AdminReferralState.waiting_new_score)

    name = user.full_name or f"ID: {user_id}"
    await message.answer(
        f"👤 <b>{name}</b>\n"
        f"🆔 <code>{user_id}</code>\n"
        f"⭐ Hozirgi referral bali: <b>{user.referral_score}</b>\n\n"
        "📝 <b>Yangi referral balini kiriting:</b>",
        parse_mode="HTML",
    )


@router.message(AdminReferralState.waiting_new_score, IsAdmin(admin_ids=ADMINS))
async def edit_score_set(message: Message, state: FSMContext):
    text = (message.text or "").strip()

    if not text.lstrip("-").isdigit():
        return await message.answer(
            "❌ <b>Faqat butun son kiriting.</b>",
            parse_mode="HTML",
        )

    new_score = int(text)

    if new_score < 0:
        return await message.answer(
            "❌ <b>Bal manfiy bo‘lishi mumkin emas.</b>",
            parse_mode="HTML",
        )

    data = await state.get_data()
    target_user_id = data["target_user_id"]

    async with session_maker() as session:
        r_service = ReferralService(session)
        success = await r_service.set_referral_score(
            user_id=target_user_id,
            score=new_score,
        )

    await state.clear()

    if success:
        await message.answer(
            f"✅ <b>Muvaffaqiyatli yangilandi!</b>\n\n"
            f"🆔 User ID: <code>{target_user_id}</code>\n"
            f"⭐ Yangi referral bali: <b>{new_score}</b>",
            parse_mode="HTML",
            reply_markup=admin_menu(),
        )
    else:
        await message.answer(
            "❌ <b>Xatolik yuz berdi. Qayta urinib ko‘ring.</b>",
            parse_mode="HTML",
            reply_markup=admin_menu(),
        )


# =========================================================
# BARCHA BALLARNI QAYTA HISOBLASH
# =========================================================


@router.callback_query(F.data == "ref_admin:recalc_all", IsAdmin(admin_ids=ADMINS))
async def recalc_all_confirm(callback: CallbackQuery):
    await callback.message.edit_text(
        "🔄 <b>Barcha foydalanuvchilar referral ballarini qayta hisoblash</b>\n\n"
        "⚠️ Bu amal barcha ro‘yxatdan o‘tgan foydalanuvchilar uchun "
        "referral ballarini qayta hisoblab chiqadi.\n\n"
        "<b>Davom etasizmi?</b>",
        parse_mode="HTML",
        reply_markup=confirm_recalc_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "ref_admin:recalc_confirm", IsAdmin(admin_ids=ADMINS))
async def recalc_all_execute(callback: CallbackQuery):
    await callback.message.edit_text(
        "⏳ <b>Qayta hisoblanmoqda...</b>",
        parse_mode="HTML",
    )
    await callback.answer()

    async with session_maker() as session:
        r_service = ReferralService(session)
        updated = await r_service.recalculate_all_referral_scores()

    await callback.message.edit_text(
        f"✅ <b>Qayta hisoblash yakunlandi!</b>\n\n"
        f"📊 Yangilangan foydalanuvchilar soni: <b>{updated}</b>",
        parse_mode="HTML",
        reply_markup=back_to_ref_menu_keyboard(),
    )
