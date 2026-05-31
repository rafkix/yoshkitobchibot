from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


CANCEL_TEXT = "❌ Bekor qilish"
SKIP_TEXT = "⏭ O'tkazib yuborish"


def cancel_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=CANCEL_TEXT)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def skip_cancel_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=SKIP_TEXT)],
            [KeyboardButton(text=CANCEL_TEXT)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def inline_back(callback_data: str, text: str = "⏪ Orqaga"):
    builder = InlineKeyboardBuilder()
    builder.button(text=text, callback_data=callback_data)
    builder.adjust(1)
    return builder.as_markup()
