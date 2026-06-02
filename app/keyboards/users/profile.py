from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


EDITABLE_FIELDS = {
    "full_name": "F.I.Sh.",
    "birth_date": "Tug‘ilgan sana",
    "location": "Yashash joyi",
    "workplace": "o‘qish yoki ish joyi",
    "phone_number": "Telefon raqami",
}


def profile_edit_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for key, label in EDITABLE_FIELDS.items():
        builder.button(text=f"{label} o‘zgartirish", callback_data=f"profile_edit:{key}")
    builder.adjust(1)
    return builder.as_markup()


def edit_fields_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for key, label in EDITABLE_FIELDS.items():
        builder.button(text=f"✏️ {label}", callback_data=f"profile_edit:{key}")
    builder.button(text="❌ Bekor qilish", callback_data="profile_edit_cancel")
    builder.adjust(1)
    return builder.as_markup()
