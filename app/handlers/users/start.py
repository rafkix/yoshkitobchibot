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
            ref_id = int(start_param)

            if ref_id != message.from_user.id:
                referred_by = ref_id

    # =========================================
    # USER
    # =========================================

    user = await service.get_user(message.from_user.id)

    if not user:
        user = await service.create_user(
            user_id=message.from_user.id,
            referred_by=referred_by,
        )
    elif referred_by is not None and user.referred_by is None:
        # Mavjud foydalanuvchida referred_by yo‘q bo‘lsa — yangilash
        await service.update_referred_by(
            user_id=message.from_user.id,
            referred_by=referred_by,
        )
        user.referred_by = referred_by

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
):
    if not callback.message or not callback.from_user:
        return await callback.answer()

    await callback.answer("Obuna tasdiqlandi")

    # Eski xabarni o‘chirish
    try:
        await callback.message.delete()
    except Exception:
        pass

    # =========================================
    # REFERRAL — callback.data dan olish: "check:12345"
    # =========================================

    referred_by = None
    if ":" in callback.data:
        param = callback.data.split(":", 1)[1]
        if param.isdigit():
            ref_id = int(param)
            if ref_id != callback.from_user.id:
                referred_by = ref_id

    # =========================================
    # USER
    # =========================================

    service = UserService(session)
    user = await service.get_user(callback.from_user.id)

    if not user:
        user = await service.create_user(
            user_id=callback.from_user.id,
            referred_by=referred_by,
        )
    elif referred_by is not None and user.referred_by is None:
        await service.update_referred_by(
            user_id=callback.from_user.id,
            referred_by=referred_by,
        )
        user.referred_by = referred_by

    # =========================================
    # ADMIN CHECK
    # =========================================

    if callback.from_user.id in ADMINS:
        await callback.message.answer(
            text="<b>Admin panel</b>\nKerakli bo‘limni tanlang.",
            reply_markup=admin_menu(),
        )
        return

    # =========================================
    # REGISTER CHECK
    # =========================================

    if not user.is_registered:
        await callback.message.answer(
            text="<b>Assalomu alaykum! Siz yangi foydalanuvchi ekansiz, avval ro‘yxatdan o‘ting.</b>",
            reply_markup=start_keyboard(),
        )
        return

    # =========================================
    # MAIN MENU
    # =========================================

    await callback.message.answer(
        text="<b>Assalomu alaykum!</b>",
        reply_markup=main_menu_keyboard(),
    )
