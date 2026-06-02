# app/handlers/admins/contest.py

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
from app.keyboards.admin_flow import (
    CANCEL_TEXT,
    SKIP_TEXT,
    cancel_reply_keyboard,
    skip_cancel_reply_keyboard,
)
from app.keyboards.reply import admin_menu
from data.config import ADMINS
from database.database import session_maker
from database.models import ContestStatus
from database.services.contest_service import ContestService
from database.services.user_service import UserService

router = Router()


# =========================================================
# STATES
# =========================================================


class ContestCreateState(StatesGroup):
    title = State()
    description = State()
    button_text = State()
    min_referrals = State()
    prize = State()


class ReferralScoreEditState(StatesGroup):
    waiting_user_id = State()
    waiting_score = State()


# =========================================================
# KEYBOARDS
# =========================================================


def contest_main_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Yangi konkurs yaratish", callback_data="cn_create")
    builder.button(text="📋 Barcha konkurslar", callback_data="cn_list")
    builder.button(text="🏆 Aktiv konkurs", callback_data="cn_active")
    builder.button(text="✏️ Referal balini sozlash", callback_data="cn_edit_score")
    builder.adjust(1)
    return builder.as_markup()


def contest_list_keyboard(contests: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for c in contests:
        icon = {"active": "🟢", "finished": "🔴", "draft": "⚪"}.get(c.status, "❓")
        builder.button(
            text=f"{icon} {c.title[:35]}",
            callback_data=f"cn_view:{c.id}",
        )
    builder.button(text="⏪ Orqaga", callback_data="cn_back_main")
    builder.adjust(1)
    return builder.as_markup()


def contest_detail_keyboard(contest) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if contest.status == ContestStatus.DRAFT:
        builder.button(text="▶️ Boshlash", callback_data=f"cn_start:{contest.id}")
    elif contest.status == ContestStatus.ACTIVE:
        builder.button(text="⏹ To‘xtatish", callback_data=f"cn_stop:{contest.id}")
        builder.button(
            text="🎲 g‘olibni tanlash", callback_data=f"cn_pick:{contest.id}"
        )
        builder.button(
            text="👥 Ishtirokchilar", callback_data=f"cn_eligible:{contest.id}"
        )

    builder.button(text="🗑 o‘chirish", callback_data=f"cn_delete:{contest.id}")
    builder.button(text="⏪ Orqaga", callback_data="cn_list")
    builder.adjust(1)
    return builder.as_markup()


def confirm_keyboard(yes_cb: str, no_cb: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Ha", callback_data=yes_cb)
    builder.button(text="❌ Yo‘q", callback_data=no_cb)
    builder.adjust(2)
    return builder.as_markup()


# =========================================================
# HELPER
# =========================================================


def contest_text(c) -> str:
    status_label = {
        ContestStatus.ACTIVE: "🟢 Aktiv",
        ContestStatus.FINISHED: "🔴 Tugagan",
        ContestStatus.DRAFT: "⚪ Qoralama",
    }.get(c.status, "❓")

    winner = f"<code>{c.winner_user_id}</code>" if c.winner_user_id else "—"
    started = c.started_at.strftime("%Y-%m-%d %H:%M") if c.started_at else "—"
    ended = c.ended_at.strftime("%Y-%m-%d %H:%M") if c.ended_at else "—"

    return (
        f"🏆 <b>{c.title}</b>\n\n"
        f"📌 <b>Holat:</b> {status_label}\n"
        f"📝 <b>Tavsif:</b> {c.description or '—'}\n"
        f"💬 <b>Foydalanuvchi matni:</b> {c.button_text or '—'}\n"
        f"👥 <b>Min referal:</b> {c.min_referrals} ta\n"
        f"🎁 <b>Sovg‘a:</b> {c.prize_description or '—'}\n\n"
        f"🗓 <b>Boshlangan:</b> {started}\n"
        f"🗓 <b>Tugagan:</b> {ended}\n"
        f"🥇 <b>g‘olib:</b> {winner}"
    )


# =========================================================
# ENTRY — "🏆 Konkurs" tugmasi
# =========================================================


@router.message(F.text == "🏆 Konkurs", IsAdmin(admin_ids=ADMINS))
async def contest_admin_menu(message: Message):
    await message.answer(
        "🏆 <b>Referal konkurs boshqaruvi</b>\n\n"
        "Bu yerda referal konkurslarni yaratib, boshqarasiz.\n"
        "Ishtirokchi shartlari bajarsa, random g‘olib tanlanadi.",
        parse_mode="HTML",
        reply_markup=contest_main_keyboard(),
    )


@router.callback_query(F.data == "cn_back_main", IsAdmin(admin_ids=ADMINS))
async def cn_back_main(callback: CallbackQuery):
    await callback.message.edit_text(
        "🏆 <b>Referal konkurs boshqaruvi</b>",
        parse_mode="HTML",
        reply_markup=contest_main_keyboard(),
    )
    await callback.answer()


# =========================================================
# BARCHA KONKURSLAR
# =========================================================


@router.callback_query(F.data == "cn_list", IsAdmin(admin_ids=ADMINS))
async def cn_list(callback: CallbackQuery):
    async with session_maker() as session:
        service = ContestService(session)
        contests = await service.get_all_contests()

    if not contests:
        await callback.message.edit_text(
            "📋 Hozircha konkurs yo‘q.\n\n➕ Yangisini yarating.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="➕ Yaratish", callback_data="cn_create"
                        ),
                        InlineKeyboardButton(
                            text="⏪ Orqaga", callback_data="cn_back_main"
                        ),
                    ]
                ]
            ),
        )
        return await callback.answer()

    await callback.message.edit_text(
        f"📋 <b>Barcha konkurslar</b> — {len(contests)} ta",
        parse_mode="HTML",
        reply_markup=contest_list_keyboard(contests),
    )
    await callback.answer()


# =========================================================
# AKTIV KONKURS
# =========================================================


@router.callback_query(F.data == "cn_active", IsAdmin(admin_ids=ADMINS))
async def cn_active(callback: CallbackQuery):
    async with session_maker() as session:
        service = ContestService(session)
        contest = await service.get_active_contest()

    if not contest:
        await callback.answer("❌ Hozircha aktiv konkurs yo‘q.", show_alert=True)
        return

    await callback.message.edit_text(
        contest_text(contest),
        parse_mode="HTML",
        reply_markup=contest_detail_keyboard(contest),
    )
    await callback.answer()


# =========================================================
# KONKURS DETAIL
# =========================================================


@router.callback_query(F.data.startswith("cn_view:"), IsAdmin(admin_ids=ADMINS))
async def cn_view(callback: CallbackQuery):
    contest_id = int(callback.data.split(":")[1])
    async with session_maker() as session:
        service = ContestService(session)
        contests = await service.get_all_contests()
        contest = next((c for c in contests if c.id == contest_id), None)

    if not contest:
        return await callback.answer("❌ Topilmadi", show_alert=True)

    await callback.message.edit_text(
        contest_text(contest),
        parse_mode="HTML",
        reply_markup=contest_detail_keyboard(contest),
    )
    await callback.answer()


# =========================================================
# KONKURS BOSHLASH
# =========================================================


@router.callback_query(F.data.startswith("cn_start:"), IsAdmin(admin_ids=ADMINS))
async def cn_start(callback: CallbackQuery):
    contest_id = int(callback.data.split(":")[1])
    async with session_maker() as session:
        service = ContestService(session)
        contest = await service.start_contest(contest_id)

    if not contest:
        return await callback.answer("❌ Topilmadi", show_alert=True)

    await callback.message.edit_text(
        f"✅ Konkurs boshlandi!\n\n{contest_text(contest)}",
        parse_mode="HTML",
        reply_markup=contest_detail_keyboard(contest),
    )
    await callback.answer("▶️ Boshlandi!")


# =========================================================
# KONKURS To‘XTATISH
# =========================================================


@router.callback_query(F.data.startswith("cn_stop:"), IsAdmin(admin_ids=ADMINS))
async def cn_stop(callback: CallbackQuery):
    contest_id = int(callback.data.split(":")[1])
    await callback.message.edit_text(
        "⏹ Haqiqatan ham konkursni to‘xtatmoqchimisiz?",
        reply_markup=confirm_keyboard(
            yes_cb=f"cn_stop_confirm:{contest_id}",
            no_cb=f"cn_view:{contest_id}",
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cn_stop_confirm:"), IsAdmin(admin_ids=ADMINS))
async def cn_stop_confirm(callback: CallbackQuery):
    contest_id = int(callback.data.split(":")[1])
    async with session_maker() as session:
        service = ContestService(session)
        contest = await service.stop_contest(contest_id)

    await callback.message.edit_text(
        f"✅ Konkurs to‘xtatildi.\n\n{contest_text(contest)}",
        parse_mode="HTML",
        reply_markup=contest_detail_keyboard(contest),
    )
    await callback.answer("⏹ To‘xtatildi!")


# =========================================================
# ISHTIROKCHILAR SONI
# =========================================================


@router.callback_query(F.data.startswith("cn_eligible:"), IsAdmin(admin_ids=ADMINS))
async def cn_eligible(callback: CallbackQuery):
    contest_id = int(callback.data.split(":")[1])
    async with session_maker() as session:
        service = ContestService(session)
        contests = await service.get_all_contests()
        contest = next((c for c in contests if c.id == contest_id), None)
        if not contest:
            return await callback.answer("❌ Topilmadi", show_alert=True)
        eligible = await service.get_eligible_users_with_counts(contest)

    text = (
        f"👥 <b>Shart bajargan ishtirokchilar</b>\n"
        f"(≥ {contest.min_referrals} ta ro‘yxatdan o‘tgan referal)\n\n"
        f"Jami: <b>{len(eligible)}</b> ta\n\n"
    )
    total_weight = sum(ref_count for _, ref_count in eligible) or 1
    for i, (u, ref_count) in enumerate(eligible[:30], 1):
        chance = (ref_count / total_weight) * 100
        text += (
            f"{i}. {u.full_name or '—'} (<code>{u.user_id}</code>) — "
            f"{ref_count} referal, imkoniyat: {chance:.1f}%\n"
        )
    if len(eligible) > 30:
        text += f"\n… va yana {len(eligible) - 30} ta"

    builder = InlineKeyboardBuilder()
    builder.button(text="⏪ Orqaga", callback_data=f"cn_view:{contest_id}")
    await callback.message.edit_text(
        text, parse_mode="HTML", reply_markup=builder.as_markup()
    )
    await callback.answer()


# =========================================================
# RANDOM g‘OLIB TANLASH
# =========================================================


@router.callback_query(F.data.startswith("cn_pick:"), IsAdmin(admin_ids=ADMINS))
async def cn_pick(callback: CallbackQuery):
    contest_id = int(callback.data.split(":")[1])
    await callback.message.edit_text(
        "🎲 Tasodifiy g‘olib tanlansinmi?\n\n"
        "Ko‘proq referal qilgan foydalanuvchining imkoniyati yuqoriroq bo‘ladi, "
        "lekin shartni bajargan har bir ishtirokchi yutishi mumkin.",
        reply_markup=confirm_keyboard(
            yes_cb=f"cn_pick_confirm:{contest_id}",
            no_cb=f"cn_view:{contest_id}",
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cn_pick_confirm:"), IsAdmin(admin_ids=ADMINS))
async def cn_pick_confirm(callback: CallbackQuery):
    contest_id = int(callback.data.split(":")[1])
    async with session_maker() as session:
        service = ContestService(session)
        contest, winner = await service.pick_winner(contest_id)

    if not contest:
        return await callback.answer("❌ Topilmadi", show_alert=True)

    if not winner:
        await callback.message.edit_text(
            "😔 Shart bajargan ishtirokchi topilmadi.\n\n"
            f"Min referal: {contest.min_referrals} ta",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="⏪ Orqaga", callback_data=f"cn_view:{contest_id}"
                        )
                    ]
                ]
            ),
        )
        return await callback.answer()

    await callback.message.edit_text(
        f"🎉 <b>g‘olib aniqlandi!</b>\n\n"
        f"🥇 <b>{winner.full_name or 'Noma‘lum'}</b>\n"
        f"🆔 <code>{winner.user_id}</code>\n"
        f"📞 {winner.phone_number or '—'}\n"
        f"🏆 Referal bali: {winner.referral_score}\n\n"
        f"Konkurs: <b>{contest.title}</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⏪ Orqaga", callback_data=f"cn_view:{contest_id}"
                    )
                ]
            ]
        ),
    )
    await callback.answer("🎉 g‘olib tanlandi!")


# =========================================================
# o‘CHIRISH
# =========================================================


@router.callback_query(F.data.startswith("cn_delete:"), IsAdmin(admin_ids=ADMINS))
async def cn_delete(callback: CallbackQuery):
    contest_id = int(callback.data.split(":")[1])
    await callback.message.edit_text(
        "🗑 Haqiqatan ham o‘chirmoqchimisiz?",
        reply_markup=confirm_keyboard(
            yes_cb=f"cn_delete_confirm:{contest_id}",
            no_cb=f"cn_view:{contest_id}",
        ),
    )
    await callback.answer()


@router.callback_query(
    F.data.startswith("cn_delete_confirm:"), IsAdmin(admin_ids=ADMINS)
)
async def cn_delete_confirm(callback: CallbackQuery):
    contest_id = int(callback.data.split(":")[1])
    async with session_maker() as session:
        service = ContestService(session)
        await service.delete_contest(contest_id)

    await callback.message.edit_text(
        "✅ Konkurs o‘chirildi.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⏪ Orqaga", callback_data="cn_list")]
            ]
        ),
    )
    await callback.answer("🗑 o‘chirildi!")


# =========================================================
# YARATISH
# =========================================================


@router.callback_query(F.data == "cn_create", IsAdmin(admin_ids=ADMINS))
async def cn_create_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ContestCreateState.title)
    await callback.message.answer(
        "➕ <b>Yangi konkurs yaratish</b>\n\n"
        "1️⃣ Konkurs nomini kiriting:\n"
        "(masalan: <i>Iyun referal yarishi</i>)",
        parse_mode="HTML",
        reply_markup=cancel_reply_keyboard(),
    )
    await callback.answer()


@router.message(ContestCreateState.title, IsAdmin(admin_ids=ADMINS))
async def cn_create_title(message: Message, state: FSMContext):
    if message.text in {"/cancel", CANCEL_TEXT}:
        await state.clear()
        return await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu())
    await state.update_data(title=message.text.strip())
    await state.set_state(ContestCreateState.description)
    await message.answer(
        "2️⃣ Konkurs tavsifini kiriting:\n"
        "Tavsif kerak bo‘lmasa, pastdagi tugmani bosing.",
        reply_markup=skip_cancel_reply_keyboard(),
    )


@router.message(ContestCreateState.description, IsAdmin(admin_ids=ADMINS))
async def cn_create_description(message: Message, state: FSMContext):
    if message.text in {"/cancel", CANCEL_TEXT}:
        await state.clear()
        return await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu())
    desc = None if message.text in {"/skip", SKIP_TEXT} else message.text.strip()
    await state.update_data(description=desc)
    await state.set_state(ContestCreateState.button_text)
    await message.answer(
        "3️⃣ Konkurs tugmasi bosilganda foydalanuvchiga chiqadigan matnni kiriting:\n"
        "Matn kerak bo‘lmasa, pastdagi tugmani bosing.",
        reply_markup=skip_cancel_reply_keyboard(),
    )


@router.message(ContestCreateState.button_text, IsAdmin(admin_ids=ADMINS))
async def cn_create_button_text(message: Message, state: FSMContext):
    if message.text in {"/cancel", CANCEL_TEXT}:
        await state.clear()
        return await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu())
    button_text = None if message.text in {"/skip", SKIP_TEXT} else message.text.strip()
    await state.update_data(button_text=button_text)
    await state.set_state(ContestCreateState.min_referrals)
    await message.answer(
        "4️⃣ Kamida nechta taklif qilingan do‘st ro‘yxatdan o‘tishi kerak?\n"
        "(raqam kiriting, masalan: <b>10</b>)",
        parse_mode="HTML",
        reply_markup=cancel_reply_keyboard(),
    )


@router.message(ContestCreateState.min_referrals, IsAdmin(admin_ids=ADMINS))
async def cn_create_min(message: Message, state: FSMContext):
    if message.text in {"/cancel", CANCEL_TEXT}:
        await state.clear()
        return await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu())
    if not message.text.isdigit() or int(message.text) < 1:
        return await message.answer("❌ Iltimos, musbat raqam kiriting.")
    await state.update_data(min_referrals=int(message.text))
    await state.set_state(ContestCreateState.prize)
    await message.answer(
        "5️⃣ Sovg‘a tavsifini kiriting:\n(masalan: <i>1 oylik Telegram Premium</i>)",
        parse_mode="HTML",
        reply_markup=skip_cancel_reply_keyboard(),
    )


@router.message(ContestCreateState.prize, IsAdmin(admin_ids=ADMINS))
async def cn_create_prize(message: Message, state: FSMContext):
    if message.text in {"/cancel", CANCEL_TEXT}:
        await state.clear()
        return await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu())
    prize = None if message.text in {"/skip", SKIP_TEXT} else message.text.strip()
    data = await state.get_data()
    await state.clear()

    async with session_maker() as session:
        service = ContestService(session)
        contest = await service.create_contest(
            title=data["title"],
            description=data.get("description"),
            button_text=data.get("button_text"),
            min_referrals=data["min_referrals"],
            prize_description=prize,
        )

    await message.answer(
        f"✅ <b>Konkurs yaratildi!</b>\n\n{contest_text(contest)}\n\n"
        "▶️ Boshlash uchun konkurs sahifasiga o‘ting.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📋 Ko‘rish", callback_data=f"cn_view:{contest.id}"
                    )
                ]
            ]
        ),
    )


# =========================================================
# REFERAL BALINI QOLDA SOZLASH (admin)
# =========================================================


@router.callback_query(F.data == "cn_edit_score", IsAdmin(admin_ids=ADMINS))
async def cn_edit_score_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ReferralScoreEditState.waiting_user_id)
    await callback.message.answer(
        "✏️ <b>Referal balini sozlash</b>\n\nFoydalanuvchi Telegram ID sini kiriting:",
        parse_mode="HTML",
        reply_markup=cancel_reply_keyboard(),
    )
    await callback.answer()


@router.message(ReferralScoreEditState.waiting_user_id, IsAdmin(admin_ids=ADMINS))
async def cn_edit_score_user(message: Message, state: FSMContext):
    if message.text in {"/cancel", CANCEL_TEXT}:
        await state.clear()
        return await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu())
    if not message.text.isdigit():
        return await message.answer("❌ Faqat raqam kiriting.")

    async with session_maker() as session:
        user = await UserService(session).get_user(int(message.text))

    if not user:
        return await message.answer("❌ Foydalanuvchi topilmadi.")

    await state.update_data(
        target_user_id=user.user_id, current_score=user.referral_score
    )
    await state.set_state(ReferralScoreEditState.waiting_score)
    await message.answer(
        f"👤 <b>{user.full_name or 'Noma‘lum'}</b> — <code>{user.user_id}</code>\n"
        f"Hozirgi referal bali: <b>{user.referral_score}</b>\n\n"
        "Yangi qiymatni kiriting (masalan: <b>+5</b>, <b>-2</b>, yoki <b>15</b>):",
        parse_mode="HTML",
        reply_markup=cancel_reply_keyboard(),
    )


@router.message(ReferralScoreEditState.waiting_score, IsAdmin(admin_ids=ADMINS))
async def cn_edit_score_value(message: Message, state: FSMContext):
    if message.text in {"/cancel", CANCEL_TEXT}:
        await state.clear()
        return await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu())

    data = await state.get_data()
    user_id = data["target_user_id"]
    current_score = data["current_score"]
    raw = message.text.strip()

    try:
        if raw.startswith("+"):
            delta = int(raw[1:])
            new_score = current_score + delta
        elif raw.startswith("-"):
            delta = -int(raw[1:])
            new_score = max(0, current_score + delta)
        else:
            new_score = int(raw)
            if new_score < 0:
                return await message.answer(
                    "❌ Ball 0 dan kichik bo‘lishi mumkin emas."
                )
    except ValueError:
        return await message.answer("❌ Noto‘g‘ri format. Masalan: +5, -2, yoki 15")

    await state.clear()

    async with session_maker() as session:
        service = UserService(session)
        user = await service.get_user(user_id)
        diff = new_score - user.referral_score
        user.referral_score = new_score
        user.total_score = max(0, user.total_score + diff)
        await session.commit()

    sign = f"+{diff}" if diff >= 0 else str(diff)
    await message.answer(
        f"✅ Referal bali yangilandi!\n\n"
        f"👤 <code>{user_id}</code>\n"
        f"📊 {current_score} → <b>{new_score}</b> ({sign})",
        parse_mode="HTML",
    )
