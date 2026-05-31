# app/handlers/users/start.py

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from sqlalchemy.ext.asyncio import AsyncSession

from database.services.user_service import UserService
from data.config import ADMINS

from app.keyboards.reply import (
    admin_menu,
    start_keyboard,
    main_menu_keyboard,
)

router = Router()


# =========================================================
# START
# =========================================================


@router.message(CommandStart())
async def start_handler(
    message: Message,
    session: AsyncSession,
):
    service = UserService(session)

    args = message.text.split()
    referred_by = None

    # =========================================
    # REFERRAL
    # =========================================

    if len(args) > 1:
        start_param = args[1]

        if start_param.isdigit():
            referred_by = int(start_param)

            if referred_by == message.from_user.id:
                referred_by = None

    # =========================================
    # USER
    # =========================================

    user = await service.get_user(message.from_user.id)

    if not user:
        user = await service.create_user(
            user_id=message.from_user.id,
            referred_by=referred_by,
        )

    # if message.from_user.id in ADMINS:
    #     return await message.answer(
    #         text="<b>Admin panel</b>\nKerakli bo'limni tanlang.",
    #         reply_markup=admin_menu(),
    #     )

    # =========================================
    # REGISTER CHECK
    # =========================================

    if not user.is_registered:
        return await message.answer(
            text="<b>Assalomu alaykum! Siz yangi foydalanuvchi ekansiz, avval ro‘yxatdan o‘ting.</b>",
            reply_markup=start_keyboard(),
        )

    # =========================================
    # MAIN MENU
    # =========================================

    await message.answer(
        text="<b>Assalomu alaykum!</b>",
        reply_markup=main_menu_keyboard(),
    )


# =========================================================
# CHECK SUBSCRIPTION CALLBACK
# — Middleware obunani tekshirib, shu handlerga o‘tkazadi
# =========================================================


@router.callback_query(F.data.startswith("check"))
async def check_subscription_callback(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    deep_link_after_subscribe: str | None = None,
):
    if not callback.message or not callback.from_user:
        return await callback.answer()

    await callback.answer("Obuna tasdiqlandi")

    # Eski xabarni o‘chirish
    try:
        await callback.message.delete()
    except Exception:
        pass

    # Foydalanuvchini tekshirish
    service = UserService(session)
    user = await service.get_user(callback.from_user.id)

    if not user:
        user = await service.create_user(user_id=callback.from_user.id)

    if callback.from_user.id in ADMINS:
        await callback.message.answer(
            text="<b>Admin panel</b>\nKerakli bo'limni tanlang.",
            reply_markup=admin_menu(),
        )
        return

    if not user.is_registered:
        await callback.message.answer(
            text="<b>Assalomu alaykum! Siz yangi foydalanuvchi ekansiz, avval ro‘yxatdan o‘ting.</b>",
            reply_markup=start_keyboard(),
        )
        return

    await callback.message.answer(
        text="<b>Assalomu alaykum!</b>",
        reply_markup=main_menu_keyboard(),
    )
