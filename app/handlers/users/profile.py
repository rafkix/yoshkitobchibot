# app/handlers/users/profile.py

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from datetime import datetime

from app.keyboards.admin_flow import CANCEL_TEXT, cancel_reply_keyboard
from app.keyboards.users.profile import EDITABLE_FIELDS, profile_edit_keyboard
from app.keyboards.reply import (
    regions_keyboard,
    districts_keyboard,
    mahallas_keyboard,
    contact_keyboard,
    regions_data,
    districts_data,
    mahallas_data,
)
from database.database import session_maker
from database.models import DirectionType
from database.services.user_service import UserService

router = Router()

DIRECTION_LABELS = {
    DirectionType.AGE_10_14: "10-14 yosh toifasi",
    DirectionType.AGE_15_19: "15-19 yosh toifasi",
    DirectionType.AGE_20_30: "20-30 yosh toifasi",
}


class EditProfileState(StatesGroup):
    edit_value = State()
    edit_region = State()
    edit_district = State()
    edit_neighborhood = State()
    edit_phone = State()


# =========================================================
# HELPERS
# =========================================================


def find_region(text: str) -> dict | None:
    return next((r for r in regions_data if r["name"] == text), None)


def find_district(region_id: int, text: str) -> dict | None:
    return next(
        (
            d
            for d in districts_data
            if d["region_id"] == region_id and d["name"] == text
        ),
        None,
    )


def find_mahalla(district_id: int, text: str) -> dict | None:
    for m in mahallas_data:
        if int(m["district_id"]) != int(district_id):
            continue
        if m.get("mfy_name") == text or m["name"] == text:
            return m
    return None


def format_birth_date(birth_date) -> str:
    if not birth_date:
        return "—"
    if isinstance(birth_date, str):
        return birth_date
    return birth_date.strftime("%d.%m.%Y")


# =========================================================
# PROFILE SHOW
# =========================================================


@router.message(F.text == "👤 Profil")
async def profile_handler(message: Message) -> None:
    user_id = message.from_user.id

    async with session_maker() as session:
        service = UserService(session)
        user = await service.get_user(user_id)

        if not user:
            return await message.answer(
                "📄 Profil topilmadi. Iltimos, ro‘yxatdan o‘ting."
            )

        # ✅ Session ichida barcha ma'lumotlarni olamiz
        location = (
            ", ".join(
                part for part in [user.region, user.district, user.neighborhood] if part
            )
            or "—"
        )

        text = (
            "<b>Sizning ma'lumotlaringiz:</b>\n\n"
            f"<b>ID:</b> <code>{message.from_user.id}</code>\n\n"
            f"<b>F.I.Sh.:</b> {user.full_name or '—'}\n"
            f"<b>Tug‘ilgan sana:</b> {format_birth_date(user.birth_date)}\n"
            f"<b>Yashash joyi:</b> {location}\n"
            f"<b>o‘qish yoki ish joyi:</b> {user.workplace or '—'}\n"
            f"<b>Telefon raqam:</b> {user.phone_number or '—'}"
        )

    await message.answer(text, parse_mode="HTML", reply_markup=profile_edit_keyboard())


# =========================================================
# EDIT — maydon tanlash
# =========================================================


@router.callback_query(F.data.startswith("profile_edit:"))
async def profile_edit_field(callback: CallbackQuery, state: FSMContext):
    field = callback.data.split(":")[1]

    if field not in EDITABLE_FIELDS:
        return await callback.answer("❌ Noto‘g‘ri maydon", show_alert=True)

    await callback.message.delete()

    # Location — alohida oqim (region → district → neighborhood)
    if field == "location":
        await state.set_state(EditProfileState.edit_region)
        await callback.message.answer(
            "🗺 <b>Hududingizni tanlang.</b>",
            parse_mode="HTML",
            reply_markup=regions_keyboard(),
        )
        await callback.answer()
        return

    # Phone — contact tugmasi bilan
    if field == "phone_number":
        await state.update_data(edit_field=field)
        await state.set_state(EditProfileState.edit_phone)
        await callback.message.answer(
            "📱 <b>Telefon raqamingizni yuboring.</b>",
            parse_mode="HTML",
            reply_markup=contact_keyboard(),
        )
        await callback.answer()
        return

    # Qolgan maydonlar — matn bilan
    await state.update_data(edit_field=field)
    await state.set_state(EditProfileState.edit_value)

    examples = {
        "full_name": "\nNamuna: <code>Abdullayev Abdullajon Abdulla o‘g‘li</code>",
        "birth_date": "\nNamuna: <code>31.01.2010</code>",
        "workplace": "\nNamuna: <code>Talaba, o‘zMU 2-kurs</code>",
    }

    label = EDITABLE_FIELDS[field]
    await callback.message.answer(
        f"✏️ <b>{label}</b> uchun yangi qiymat kiriting.{examples.get(field, '')}",
        parse_mode="HTML",
        reply_markup=cancel_reply_keyboard(),
    )
    await callback.answer()


# =========================================================
# EDIT — matn qiymati (full_name, birth_date, workplace)
# =========================================================


@router.message(EditProfileState.edit_value)
async def profile_edit_save(message: Message, state: FSMContext):
    if message.text and message.text.strip() in {"/cancel", CANCEL_TEXT}:
        await state.clear()
        return await message.answer(
            "❌ Bekor qilindi.",
            reply_markup=ReplyKeyboardRemove(),
        )

    data = await state.get_data()
    field = data.get("edit_field")
    value = message.text.strip() if message.text else None

    if not field or not value:
        return await message.answer("❌ Qiymat kiritilmadi.")

    update_data = {}

    if field == "birth_date":
        try:
            update_data["birth_date"] = datetime.strptime(value, "%d.%m.%Y").date()
        except ValueError:
            return await message.answer(
                "❌ Sana noto‘g‘ri formatda.\nNamuna: <code>31.01.2010</code>",
                parse_mode="HTML",
            )
    else:
        update_data[field] = value

    async with session_maker() as session:
        service = UserService(session)
        await service.update_user(message.from_user.id, **update_data)

    await state.clear()

    label = EDITABLE_FIELDS.get(field, field)
    await message.answer(
        f"✅ <b>{label}</b> muvaffaqiyatli yangilandi!",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )
    await profile_handler(message)


# =========================================================
# EDIT — location: region
# =========================================================


@router.message(EditProfileState.edit_region)
async def profile_edit_region(message: Message, state: FSMContext):
    if message.text and message.text.strip() in {"/cancel", CANCEL_TEXT}:
        await state.clear()
        return await message.answer(
            "❌ Bekor qilindi.",
            reply_markup=ReplyKeyboardRemove(),
        )

    selected = find_region(message.text)
    if not selected:
        return await message.answer(
            "⚠️ Hududni tugmalar orqali tanlang.",
            reply_markup=regions_keyboard(),
        )

    await state.update_data(
        region=selected["name"],
        region_id=selected["id"],
        district=None,
        district_id=None,
        neighborhood=None,
    )
    await state.set_state(EditProfileState.edit_district)
    await message.answer(
        "🏙 <b>Tuman/shaharni tanlang.</b>",
        parse_mode="HTML",
        reply_markup=districts_keyboard(selected["id"]),
    )


# =========================================================
# EDIT — location: district
# =========================================================


@router.message(EditProfileState.edit_district)
async def profile_edit_district(message: Message, state: FSMContext):
    if message.text and message.text.strip() in {"/cancel", CANCEL_TEXT}:
        await state.clear()
        return await message.answer(
            "❌ Bekor qilindi.",
            reply_markup=ReplyKeyboardRemove(),
        )

    data = await state.get_data()
    region_id = data.get("region_id")

    selected = find_district(region_id, message.text)
    if not selected:
        return await message.answer(
            "⚠️ Tumanni tugmalar orqali tanlang.",
            reply_markup=districts_keyboard(region_id),
        )

    await state.update_data(
        district=selected["name"],
        district_id=selected["id"],
        neighborhood=None,
    )
    await state.set_state(EditProfileState.edit_neighborhood)
    await message.answer(
        "🏘 <b>Mahallani tanlang.</b>",
        parse_mode="HTML",
        reply_markup=mahallas_keyboard(selected["id"]),
    )


# =========================================================
# EDIT — location: neighborhood
# =========================================================


@router.message(EditProfileState.edit_neighborhood)
async def profile_edit_neighborhood(message: Message, state: FSMContext):
    if message.text and message.text.strip() in {"/cancel", CANCEL_TEXT}:
        await state.clear()
        return await message.answer(
            "❌ Bekor qilindi.",
            reply_markup=ReplyKeyboardRemove(),
        )

    data = await state.get_data()
    district_id = data.get("district_id")

    selected = find_mahalla(district_id, message.text)
    if not selected:
        return await message.answer(
            "⚠️ Mahallani tugmalar orqali tanlang.",
            reply_markup=mahallas_keyboard(district_id),
        )

    update_data = {
        "region": data["region"],
        "district": data["district"],
        "neighborhood": selected.get("mfy_name") or selected["name"],
    }

    async with session_maker() as session:
        service = UserService(session)
        await service.update_user(message.from_user.id, **update_data)

    await state.clear()
    await message.answer(
        "✅ <b>Yashash joyi</b> muvaffaqiyatli yangilandi!",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )
    await profile_handler(message)


# =========================================================
# EDIT — phone number (contact)
# =========================================================


@router.message(EditProfileState.edit_phone, F.contact)
async def profile_edit_phone(message: Message, state: FSMContext):
    phone = message.contact.phone_number

    async with session_maker() as session:
        service = UserService(session)
        await service.update_user(message.from_user.id, phone_number=phone)

    await state.clear()
    await message.answer(
        "✅ <b>Telefon raqam</b> muvaffaqiyatli yangilandi!",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )
    await profile_handler(message)


@router.message(EditProfileState.edit_phone)
async def profile_edit_phone_invalid(message: Message, state: FSMContext):
    if message.text and message.text.strip() in {"/cancel", CANCEL_TEXT}:
        await state.clear()
        return await message.answer(
            "❌ Bekor qilindi.",
            reply_markup=ReplyKeyboardRemove(),
        )

    await message.answer(
        "📱 Iltimos, <b>«Telefon raqamni yuborish»</b> tugmasini bosing.",
        parse_mode="HTML",
        reply_markup=contact_keyboard(),
    )


# =========================================================
# CANCEL
# =========================================================


@router.callback_query(F.data == "profile_edit_cancel")
async def profile_edit_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Bekor qilindi.")
    await callback.answer()
