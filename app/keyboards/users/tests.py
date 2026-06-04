import random

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

EMOJIS = ["📗", "📘", "📙", "📕"]


def tests_list_keyboard(tests: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for test in tests:
        builder.button(
            text=f"{random.choice(EMOJIS)} {test.title}",
            callback_data=f"pick_test:{test.id}",
        )

    builder.adjust(1)
    return builder.as_markup()


def start_test_keyboard(test_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(
        text="🚀 Boshlash",
        callback_data=f"start_test:{test_id}",
    )

    builder.button(
        text="🔙 Orqaga",
        callback_data="back_to_tests",
    )

    builder.adjust(1)
    return builder.as_markup()


def question_keyboard(question_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for option in ("A", "B", "C", "D"):
        builder.button(
            text=option,
            callback_data=f"ans:{question_id}:{option}",
        )

    builder.adjust(4)

    return builder.as_markup()
