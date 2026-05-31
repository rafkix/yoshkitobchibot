from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from database.database import session_maker
from database.models import CustomButton

router = Router()


async def get_active_buttons() -> list[CustomButton]:
    async with session_maker() as session:
        result = await session.execute(
            select(CustomButton)
            .where(CustomButton.is_active.is_(True))
            .order_by(CustomButton.position, CustomButton.id)
        )
        return result.scalars().all()


def custom_buttons_keyboard(buttons: list[CustomButton]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for button in buttons:
        if button.action_type == "url" and button.action_value:
            builder.row(InlineKeyboardButton(text=button.text, url=button.action_value))
        else:
            builder.button(text=button.text, callback_data=f"ucb:{button.id}")
    builder.adjust(1)
    return builder.as_markup()


@router.message(F.text == "🔘 Qo'shimcha")
async def show_custom_buttons(message: Message):
    buttons = await get_active_buttons()
    if not buttons:
        return await message.answer("Hozircha qo'shimcha tugmalar mavjud emas.")

    await message.answer(
        "Kerakli bo'limni tanlang:",
        reply_markup=custom_buttons_keyboard(buttons),
    )


@router.callback_query(F.data.startswith("ucb:"))
async def custom_button_callback(callback: CallbackQuery):
    button_id = int(callback.data.split(":")[1])
    async with session_maker() as session:
        result = await session.execute(
            select(CustomButton).where(
                CustomButton.id == button_id,
                CustomButton.is_active.is_(True),
            )
        )
        button = result.scalar_one_or_none()

    if not button:
        return await callback.answer("Tugma topilmadi yoki o'chirilgan.", show_alert=True)

    if button.action_type == "message" and button.action_value:
        await callback.message.answer(button.action_value, parse_mode="HTML")
    elif button.action_type == "url" and button.action_value:
        await callback.message.answer(
            "Havolani ochish uchun tugmani bosing:",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=button.text, url=button.action_value)]
                ]
            ),
        )
    else:
        await callback.answer("Bu tugma uchun amal sozlanmagan.", show_alert=True)
        return

    await callback.answer()
