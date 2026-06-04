# app/handlers/users/start.py

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.keyboards.reply import (
    main_menu_keyboard,
    start_keyboard,
)
from database.database import session_maker
from database.services.user_service import UserService

router = Router()


async def get_or_create_user(
    user_id: int,
    referred_by: int | None,
    service: UserService,
):
    user = await service.get_user(user_id)

    if not user:
        return await service.create_user(
            user_id=user_id,
            referred_by=referred_by,
        )

    # ✅ referred_by faqat bir marta o‘rnatiladi, o‘ziga referral bo‘lolmaydi
    if referred_by and user.referred_by is None and referred_by != user_id:
        await service.update_referred_by(
            user_id=user_id,
            referred_by=referred_by,
        )
        user.referred_by = referred_by

    return user


def extract_referral_id(
    start_param: str | None,
    user_id: int,
) -> int | None:
    if not start_param:
        return None

    if not start_param.isdigit():
        return None

    referrer_id = int(start_param)

    if referrer_id == user_id:
        return None

    return referrer_id


@router.message(CommandStart())
async def start_handler(message: Message):
    args = message.text.split(maxsplit=1)

    referred_by = extract_referral_id(
        args[1] if len(args) > 1 else None,
        message.from_user.id,
    )

    async with session_maker() as session:  # ✅ session_maker orqali session olinadi
        service = UserService(session)

        user = await get_or_create_user(
            user_id=message.from_user.id,
            referred_by=referred_by,
            service=service,
        )

    if not user.is_registered:
        await message.answer(
            text=(
                "<b>Assalomu alaykum!</b>\n\n"
                "Botdan foydalanish uchun "
                "ro‘yxatdan o‘ting."
            ),
            parse_mode="HTML",
            reply_markup=start_keyboard(),
        )
        return

    await message.answer(
        text="<b>Assalomu alaykum!</b>",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )


@router.callback_query(F.data.startswith("check"))
async def check_subscription_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not callback.message:
        return await callback.answer()

    await callback.answer("Obuna tasdiqlandi ✅")

    try:
        await callback.message.delete()
    except Exception:
        pass

    referred_by = None

    if ":" in callback.data:
        start_param = callback.data.split(":", maxsplit=1)[1]
        referred_by = extract_referral_id(
            start_param,
            callback.from_user.id,
        )

    async with session_maker() as session:  # ✅ session_maker orqali session olinadi
        service = UserService(session)

        user = await get_or_create_user(
            user_id=callback.from_user.id,
            referred_by=referred_by,
            service=service,
        )

    if not user.is_registered:
        await callback.message.answer(
            text=(
                "<b>Assalomu alaykum!</b>\n\n"
                "Botdan foydalanish uchun "
                "ro‘yxatdan o‘ting."
            ),
            parse_mode="HTML",
            reply_markup=start_keyboard(),
        )
        return

    await callback.message.answer(
        text="<b>Assalomu alaykum!</b>",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )
