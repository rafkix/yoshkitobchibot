import asyncio

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import (
    TelegramForbiddenError,
    TelegramBadRequest,
    TelegramRetryAfter,
)

from app.filters.is_admin import IsAdmin
from app.keyboards.inline import admin_ads_send, cancel_ads_keyboard
from app.states.ads import SendAds, SendCopy
from data.config import ADMINS

from database.services.user_service import get_all_users
from database.database import session_maker

router = Router()


BATCH_SIZE = 25
BATCH_DELAY = 1.0


@router.callback_query(F.data == "admin_ads_send", IsAdmin(admin_ids=ADMINS))
async def admin_ads_send_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "Yuborish turini tanlang:",
        reply_markup=admin_ads_send()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_send_forward", IsAdmin(admin_ids=ADMINS))
async def admin_send_forward(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SendAds.send_forward)
    await callback.message.edit_text(
        "📩 Reklama yuborish uchun xabarni FORWARD qiling.\n\n",
        reply_markup=cancel_ads_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_send_copy", IsAdmin(admin_ids=ADMINS))
async def send_copy(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SendCopy.send_copy)
    await callback.message.edit_text(
        "📋 Reklama uchun xabar yuboring.\n\n",
        reply_markup=cancel_ads_keyboard()
    )
    await callback.answer()


@router.callback_query(
    F.data == "cancel_add_ads",
    IsAdmin(admin_ids=ADMINS),
)
async def cancel_ads_callback(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()

    if current_state not in {
        SendAds.send_forward.state,
        SendCopy.send_copy.state,
    }:
        return await callback.answer("Bekor qilish uchun holat yo‘q", show_alert=True)

    await state.clear()

    await callback.message.edit_text("❌ Bekor qilindi.",reply_markup=admin_ads_send())
    await callback.answer()

async def fetch_active_users():
    async with session_maker() as session:
        users = await get_all_users(session, active_only=True)
        return users


async def safe_forward(bot: Bot, user_id: int, source_message: Message) -> tuple[bool, str | None]:
    try:
        await bot.forward_message(
            chat_id=user_id,
            from_chat_id=source_message.chat.id,
            message_id=source_message.message_id,
        )
        return True, None

    except TelegramForbiddenError:
        return False, "forbidden"

    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after)
        try:
            await bot.forward_message(
                chat_id=user_id,
                from_chat_id=source_message.chat.id,
                message_id=source_message.message_id,
            )
            return True, None
        except Exception:
            return False, "retry_failed"

    except TelegramBadRequest:
        return False, "bad_request"

    except Exception:
        return False, "unknown"


async def safe_copy(bot: Bot, user_id: int, source_message: Message) -> tuple[bool, str | None]:
    try:
        await bot.copy_message(
            chat_id=user_id,
            from_chat_id=source_message.chat.id,
            message_id=source_message.message_id,
        )
        return True, None

    except TelegramForbiddenError:
        return False, "forbidden"

    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after)
        try:
            await bot.copy_message(
                chat_id=user_id,
                from_chat_id=source_message.chat.id,
                message_id=source_message.message_id,
            )
            return True, None
        except Exception:
            return False, "retry_failed"

    except TelegramBadRequest:
        return False, "bad_request"

    except Exception:
        return False, "unknown"


async def run_broadcast(
    message: Message,
    state: FSMContext,
    mode: str,
    bot: Bot,
):
    users = await fetch_active_users()

    total = len(users)
    success = 0
    failed = 0
    forbidden = 0

    status_msg = await message.answer(f"🚀 Yuborish boshlandi...\n👥 Jami: {total}")

    for i, user in enumerate(users, start=1):
        if mode == "forward":
            ok, reason = await safe_forward(bot, user.user_id, message)
        else:
            ok, reason = await safe_copy(bot, user.user_id, message)

        if ok:
            success += 1
        else:
            failed += 1
            if reason == "forbidden":
                forbidden += 1
                # shu yerda user'ni inactive qilish mumkin

        if i % BATCH_SIZE == 0:
            await asyncio.sleep(BATCH_DELAY)

        if i % 100 == 0 or i == total:
            await status_msg.edit_text(
                f"🚀 Yuborilmoqda...\n"
                f"👥 Jami: {total}\n"
                f"✅ Yuborildi: {success}\n"
                f"❌ Xatolik: {failed}\n"
                f"⛔ Block/Admin stop: {forbidden}\n"
                f"📊 Progress: {i}/{total}"
            )

    await message.answer(
        f"✅ Reklama yakunlandi\n\n"
        f"👥 Jami: {total}\n"
        f"📤 Yuborildi: {success}\n"
        f"❌ Xatolik: {failed}\n"
        f"⛔ Block/Admin stop: {forbidden}"
    )

    await state.clear()


@router.message(
    F.forward_from | F.forward_from_chat,
    SendAds.send_forward,
    IsAdmin(admin_ids=ADMINS)
)
async def send_ads_forward(message: Message, state: FSMContext, bot: Bot):
    await run_broadcast(
        message=message,
        state=state,
        mode="forward",
        bot=bot,
    )


@router.message(
    SendCopy.send_copy,
    IsAdmin(admin_ids=ADMINS)
)
async def send_ads_copy(message: Message, state: FSMContext, bot: Bot):
    await run_broadcast(
        message=message,
        state=state,
        mode="copy",
        bot=bot,
    )