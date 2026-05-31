from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime

from aiogram.types import CallbackQuery, Message

from app.keyboards.admin_flow import CANCEL_TEXT, cancel_reply_keyboard
from app.keyboards.users.profile import (
    EDITABLE_FIELDS,
    profile_edit_keyboard,
)
from database.database import session_maker
from database.models import ContestType, DirectionType
from database.services.user_service import UserService

router = Router()

DIRECTION_LABELS = {
    DirectionType.AGE_10_14: "10-14 yosh toifasi",
    DirectionType.AGE_15_19: "15-19 yosh toifasi",
    DirectionType.AGE_20_30: "20-30 yosh toifasi",
}


class EditProfileState(StatesGroup):
    edit_value = State()


@router.message(F.text == "👤 Profil")
async def profile_handler(message: Message) -> None:
    user_id = message.from_user.id

    async with session_maker() as session:
        service = UserService(session)
        user = await service.get_user(user_id)
        if not user:
            return await message.answer(
                "📄 Profil topilmadi. Iltimos, ro'yxatdan o'ting."
            )

    location = ", ".join(
        part for part in [user.region, user.district, user.neighborhood] if part
    ) or "—"
    text = (
        "<b>Sizning ma'lumotlaringiz:</b>\n\n"
        f"<b>F.I.Sh.:</b> {user.full_name or '—'}\n"
        f"<b>Tug'ilgan sanangiz:</b> {user.birth_date or '—'}\n"
        f"<b>Yashash joyingiz:</b> {location}\n"
        f"<b>O'qish yoki ish joyingiz:</b> {user.workplace or '—'}\n"
        f"<b>Telefon raqamingiz:</b> {user.phone_number or '—'}"
    )

    await message.answer(text, parse_mode="HTML", reply_markup=profile_edit_keyboard())


@router.callback_query(F.data == "profile_edit_cancel")
async def profile_edit_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Bekor qilindi.")
    await callback.answer()


@router.callback_query(F.data.startswith("profile_edit:"))
async def profile_edit_field(callback: CallbackQuery, state: FSMContext):
    field = callback.data.split(":")[1]
    if field not in EDITABLE_FIELDS:
        return await callback.answer("❌ Noto'g'ri maydon", show_alert=True)

    await state.update_data(edit_field=field)
    await state.set_state(EditProfileState.edit_value)

    label = EDITABLE_FIELDS[field]
    examples = {
        "birth_date": "\nNamuna: <code>31.01.2010</code>",
        "location": "\nNamuna: <code>Farg'ona viloyati, Qo'shtepa tuman, Xo'jaqishloq</code>",
        "phone_number": "\nNamuna: <code>+998901234567</code>",
    }
    await callback.message.edit_text(
        f"✏️ <b>{label}</b> uchun yangi qiymat kiriting."
        f"{examples.get(field, '')}",
        parse_mode="HTML",
    )
    await callback.message.answer(
        "Bekor qilish uchun pastdagi tugmani bosing.",
        reply_markup=cancel_reply_keyboard(),
    )
    await callback.answer()


@router.message(EditProfileState.edit_value)
async def profile_edit_save(message: Message, state: FSMContext):
    if message.text and message.text.strip() in {"/cancel", CANCEL_TEXT}:
        await state.clear()
        return await message.answer("❌ Bekor qilindi.")

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
                "❌ Sana noto'g'ri. Namuna: <code>31.01.2010</code>",
                parse_mode="HTML",
            )
    elif field == "location":
        parts = [part.strip() for part in value.split(",") if part.strip()]
        update_data["region"] = parts[0] if len(parts) > 0 else value
        update_data["district"] = parts[1] if len(parts) > 1 else None
        update_data["neighborhood"] = ", ".join(parts[2:]) if len(parts) > 2 else None
    elif field == "phone_number":
        update_data["phone_number"] = value
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
    )
    await profile_handler(message)
