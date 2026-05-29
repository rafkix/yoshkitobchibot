# app/handlers/admins/users.py

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.filters.is_admin import IsAdmin
from app.keyboards.reply import admin_menu
from data.config import ADMINS
from database.database import session_maker
from database.models import DirectionType, ContestType
from database.services.user_service import UserService

router = Router()

# =========================================================
# CONSTANTS
# =========================================================

DIRECTION_LABELS = {
    DirectionType.AGE_10_14: "10-14 yosh toifasi (2012-2016)",
    DirectionType.AGE_15_19: "15-19 yosh toifasi (2007-2011)",
    DirectionType.AGE_20_30: "20-30 yosh toifasi (1996-2006)",
}

CONTEST_LABELS = {
    ContestType.YOSH_KITOBXON_2026: '“Yosh kitobchi” - 2026 yoz',
}

PAGE_SIZE = 10


# =========================================================
# STATES
# =========================================================

class UserSearchState(StatesGroup):
    waiting_query = State()


# =========================================================
# HELPERS
# =========================================================

def user_detail_text(user, referrals_total: int, referrals_registered: int) -> str:
    direction = DIRECTION_LABELS.get(user.direction, "—")
    contest = CONTEST_LABELS.get(user.contest, "—")
    status = "✅ Ro‘yxatdan o‘tgan" if user.is_registered else "⏳ Ro‘yxatdan o‘tmagan"

    # referred_by
    ref_by = f"<code>{user.referred_by}</code>" if user.referred_by else "—"

    return (
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "👤 <b>FOYDALANUVCHI MA'LUMOTLARI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"

        "🪪 <b>Shaxsiy ma'lumotlar</b>\n"
        f"  <b>Telegram ID:</b> <code>{user.user_id}</code>\n"
        f"  <b>F.I.Sh.:</b> {user.full_name or '—'}\n"
        f"  <b>Tug‘ilgan sana:</b> {user.birth_date or '—'}\n"
        f"  <b>Telefon:</b> <code>{user.phone_number or '—'}</code>\n\n"

        "📍 <b>Manzil</b>\n"
        f"  <b>Viloyat:</b> {user.region or '—'}\n"
        f"  <b>Tuman:</b> {user.district or '—'}\n"
        f"  <b>Mahalla:</b> {user.neighborhood or '—'}\n\n"

        "🏫 <b>Ish / o‘qish joyi</b>\n"
        f"  {user.workplace or '—'}\n\n"

        "🏆 <b>Tanlov ma'lumotlari</b>\n"
        f"  <b>Tanlov:</b> {contest}\n"
        f"  <b>Yo‘nalish:</b> {direction}\n\n"

        "📊 <b>Balllar</b>\n"
        f"  <b>Umumiy:</b> {user.total_score} ball\n"
        f"  ├ Test ballari: {user.test_score}\n"
        f"  └ Referal ballari: {user.referral_score}\n\n"

        "👥 <b>Referal statistikasi</b>\n"
        f"  <b>Kim taklif qilgan:</b> {ref_by}\n"
        f"  <b>U taklif qilganlar:</b> {referrals_total} ta\n"
        f"  └ Ro‘yxatdan o‘tganlari: {referrals_registered} ta (ball berilgan)\n\n"

        f"📌 <b>Holat:</b> {status}\n"
        f"📅 <b>Qo‘shilgan:</b> {user.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        "━━━━━━━━━━━━━━━━━━━━━"
    )


def users_list_keyboard(
    users: list,
    page: int,
    total: int,
    search_query: str = "",
    filter_mode: str = "all",
):
    builder = InlineKeyboardBuilder()

    for u in users:
        name = u.full_name or f"Foydalanuvchi"
        status = "✅" if u.is_registered else "⏳"
        # Telegram ID qisqartirilgan + ball
        label = f"{status} {name[:28]} | {u.total_score}б"
        builder.button(
            text=label,
            callback_data=f"admuv:{u.user_id}:{page}:{filter_mode}:{search_query[:20]}",
        )

    builder.adjust(1)

    # --- Filter tugmalari ---
    filters = [
        ("👥 Barchasi", "all"),
        ("✅ o‘tganlar", "reg"),
        ("⏳ o‘tmaganlar", "unreg"),
    ]
    for label, mode in filters:
        prefix = "▶️ " if filter_mode == mode else ""
        builder.button(
            text=f"{prefix}{label}",
            callback_data=f"admuf:{mode}:0:",
        )
    builder.adjust(3)

    # --- Pagination ---
    nav_row = []
    if page > 0:
        nav_row.append(
            ("⬅️", f"admup:{page - 1}:{filter_mode}:{search_query[:20]}")
        )
    nav_row.append(
        ("📄 " + str(page + 1), "admup_noop")
    )
    if (page + 1) * PAGE_SIZE < total:
        nav_row.append(
            ("➡️", f"admup:{page + 1}:{filter_mode}:{search_query[:20]}")
        )
    for text, cb in nav_row:
        builder.button(text=text, callback_data=cb)
    builder.adjust(len(nav_row))

    # --- Qidirish va orqaga ---
    builder.button(text="🔍 Qidirish", callback_data="admus")
    builder.button(text="⏪ Orqaga", callback_data="admub")
    builder.adjust(2)

    return builder.as_markup()


def user_detail_keyboard(user_id: int, back_page: int = 0, filter_mode: str = "all", search_query: str = ""):
    builder = InlineKeyboardBuilder()
    builder.button(
        text="💬 Xabar yuborish",
        callback_data=f"admum:{user_id}",
    )
    builder.button(
        text="⏪ Ro‘yxatga qaytish",
        callback_data=f"admup:{back_page}:{filter_mode}:{search_query[:20]}",
    )
    builder.adjust(1)
    return builder.as_markup()


async def get_filtered_users(service: UserService, filter_mode: str) -> list:
    if filter_mode == "reg":
        return await service.get_all_users(registered_only=True)
    elif filter_mode == "unreg":
        all_users = await service.get_all_users()
        return [u for u in all_users if not u.is_registered]
    else:
        return await service.get_all_users()


def build_list_text(users: list, page: int, total: int, filter_mode: str, search_query: str = "") -> str:
    start = page * PAGE_SIZE
    end = min(start + PAGE_SIZE, total)

    filter_names = {"all": "Barchasi", "reg": "✅ Ro‘yxatdan o‘tganlar", "unreg": "⏳ o‘tmaganlar"}
    header = filter_names.get(filter_mode, "Barchasi")

    text = (
        f"👥 <b>Foydalanuvchilar — {header}</b>\n\n"
        f"📊 Jami: <b>{total}</b> ta"
    )
    if total > 0:
        text += f" | Ko‘rsatilmoqda: <b>{start + 1}–{end}</b>"
    if search_query:
        text += f"\n🔍 Qidiruv: <i>{search_query}</i>"
    return text


# =========================================================
# ENTRY — "👥 Foydalanuvchilar" tugmasi
# =========================================================

@router.message(F.text == "👥 Foydalanuvchilar", IsAdmin(admin_ids=ADMINS))
async def admin_users_menu(message: Message, state: FSMContext):
    await state.clear()
    async with session_maker() as session:
        service = UserService(session)
        all_users = await service.get_all_users()

    total = len(all_users)
    reg = sum(1 for u in all_users if u.is_registered)
    unreg = total - reg
    page_users = all_users[:PAGE_SIZE]

    text = (
        "👥 <b>Foydalanuvchilar bo‘limi</b>\n\n"
        f"📊 Jami: <b>{total}</b> ta\n"
        f"  ✅ Ro‘yxatdan o‘tgan: <b>{reg}</b> ta\n"
        f"  ⏳ o‘tmagan: <b>{unreg}</b> ta\n\n"
        "Foydalanuvchi ustiga bosib to‘liq ma'lumotini ko‘ring."
    )

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=users_list_keyboard(page_users, 0, total),
    )


# =========================================================
# FILTER
# =========================================================

@router.callback_query(F.data.startswith("admuf:"), IsAdmin(admin_ids=ADMINS))
async def admin_users_filter(callback: CallbackQuery):
    parts = callback.data.split(":", 3)
    filter_mode = parts[1]
    page = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
    search_query = parts[3] if len(parts) > 3 else ""

    async with session_maker() as session:
        service = UserService(session)
        users = await get_filtered_users(service, filter_mode)

    total = len(users)
    page_users = users[page * PAGE_SIZE: (page + 1) * PAGE_SIZE]

    await callback.message.edit_text(
        build_list_text(users, page, total, filter_mode, search_query),
        parse_mode="HTML",
        reply_markup=users_list_keyboard(page_users, page, total, search_query, filter_mode),
    )
    await callback.answer()


# =========================================================
# PAGINATION
# =========================================================

@router.callback_query(F.data == "admup_noop", IsAdmin(admin_ids=ADMINS))
async def noop(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data.startswith("admup:"), IsAdmin(admin_ids=ADMINS))
async def admin_users_page(callback: CallbackQuery):
    parts = callback.data.split(":", 3)
    page = int(parts[1])
    filter_mode = parts[2] if len(parts) > 2 else "all"
    search_query = parts[3] if len(parts) > 3 else ""

    async with session_maker() as session:
        service = UserService(session)
        if search_query:
            users = await service.search_users(search_query)
        else:
            users = await get_filtered_users(service, filter_mode)

    total = len(users)
    start = page * PAGE_SIZE
    page_users = users[start: start + PAGE_SIZE]

    await callback.message.edit_text(
        build_list_text(users, page, total, filter_mode, search_query),
        parse_mode="HTML",
        reply_markup=users_list_keyboard(page_users, page, total, search_query, filter_mode),
    )
    await callback.answer()


# =========================================================
# USER DETAIL
# =========================================================

@router.callback_query(F.data.startswith("admuv:"), IsAdmin(admin_ids=ADMINS))
async def admin_user_detail(callback: CallbackQuery):
    # admuv:{user_id}:{page}:{filter_mode}:{search_query}
    parts = callback.data.split(":", 4)
    user_id = int(parts[1])
    back_page = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
    filter_mode = parts[3] if len(parts) > 3 else "all"
    search_query = parts[4] if len(parts) > 4 else ""

    async with session_maker() as session:
        service = UserService(session)
        user = await service.get_user(user_id)
        if not user:
            return await callback.answer("❌ Foydalanuvchi topilmadi", show_alert=True)

        referrals_total = await service.get_referrals_count(user_id)
        referrals_registered = await service.get_registered_referrals_count(user_id)

    await callback.message.edit_text(
        user_detail_text(user, referrals_total, referrals_registered),
        parse_mode="HTML",
        reply_markup=user_detail_keyboard(user_id, back_page, filter_mode, search_query),
    )
    await callback.answer()


# =========================================================
# MESSAGE TO USER — adminga user_id ga xabar yuborish
# =========================================================

@router.callback_query(F.data.startswith("admum:"), IsAdmin(admin_ids=ADMINS))
async def admin_message_to_user_start(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split(":")[1])
    await state.update_data(message_target_user_id=user_id)
    await state.set_state(UserSearchState.waiting_query)
    await callback.message.answer(
        f"✉️ <b>Foydalanuvchiga xabar</b>\n\n"
        f"<code>{user_id}</code> ga yuboriladigan xabarni kiriting:\n"
        f"(Bekor qilish uchun /cancel)",
        parse_mode="HTML",
    )
    await callback.answer()


# =========================================================
# SEARCH — qidirish
# =========================================================

@router.callback_query(F.data == "admus", IsAdmin(admin_ids=ADMINS))
async def admin_users_search_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserSearchState.waiting_query)
    await state.update_data(message_target_user_id=None)
    await callback.message.answer(
        "🔍 <b>Foydalanuvchi qidirish</b>\n\n"
        "Quyidagilardan birini kiriting:\n"
        "• <b>Ism</b> yoki ism qismi\n"
        "• <b>Telefon raqam</b>\n"
        "• <b>Telegram ID</b> (raqam)\n\n"
        "(Bekor qilish: /cancel)",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(UserSearchState.waiting_query, IsAdmin(admin_ids=ADMINS))
async def admin_users_search_or_message(message: Message, state: FSMContext):
    if message.text and message.text.strip() == "/cancel":
        await state.clear()
        return await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu())

    data = await state.get_data()
    target_user_id = data.get("message_target_user_id")

    # Xabar yuborish rejimi
    if target_user_id:
        await state.clear()
        try:
            await message.bot.send_message(
                chat_id=target_user_id,
                text=f"📩 <b>Admin xabari:</b>\n\n{message.text}",
                parse_mode="HTML",
            )
            await message.answer(
                f"✅ Xabar <code>{target_user_id}</code> ga yuborildi.",
                parse_mode="HTML",
            )
        except Exception as e:
            await message.answer(
                f"❌ Xabar yuborib bo‘lmadi: <code>{e}</code>",
                parse_mode="HTML",
            )
        return

    # Qidiruv rejimi
    query = message.text.strip()
    await state.clear()

    async with session_maker() as session:
        service = UserService(session)
        if query.isdigit():
            user = await service.get_user(int(query))
            users = [user] if user else []
        else:
            users = await service.search_users(query)

    total = len(users)

    if not users:
        return await message.answer(
            f"❌ <b>'{query}'</b> bo‘yicha hech narsa topilmadi.\n\n"
            "Qayta urinib ko‘ring.",
            parse_mode="HTML",
        )

    text = (
        f"🔍 <b>Qidiruv:</b> <i>{query}</i>\n"
        f"📊 Topildi: <b>{total}</b> ta"
    )

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=users_list_keyboard(users[:PAGE_SIZE], 0, total, query),
    )


# =========================================================
# BACK
# =========================================================

@router.callback_query(F.data == "admub", IsAdmin(admin_ids=ADMINS))
async def admin_users_back(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(
        "🔐 Admin panel\nKerakli bo‘limni tanlang.",
        reply_markup=admin_menu(),
    )
    await callback.answer()
