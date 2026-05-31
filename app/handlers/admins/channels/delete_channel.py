from aiogram import Router, F
from aiogram.types import CallbackQuery

from app.filters.is_admin import IsAdmin
from app.keyboards.inline import (
    admin_channel,
    delete_channels_list_keyboard,
    delete_channel_success_keyboard,
)
from data.config import ADMINS
from database.services.channel_service import (
    count_channels,
    get_all_channels,
    get_channel_by_id,
    set_channel_active,
)
from database.database import session_maker

router = Router()


@router.callback_query(F.data == "delete_channels", IsAdmin(admin_ids=ADMINS))
async def show_delete_channels_list(callback: CallbackQuery):
    if not callback.message:
        await callback.answer()
        return

    async with session_maker() as session:
        total = await count_channels(session, active_only=True)
        channels = await get_all_channels(session, active_only=True)

    if not channels:
        await callback.message.edit_text(
            "📋 <b>Majburiy obuna kanallari ro‘yxati:</b>\n\n"
            "❌ o‘chirish uchun kanal topilmadi.",
            parse_mode="HTML",
            reply_markup=await admin_channel(),
        )
        await callback.answer()
        return

    text = (
        "📋 <b>Majburiy obuna kanallari ro‘yxati:</b>\n\n"
        f"🔢 <b>Jami:</b> {total} ta\n\n"
        "🗑 o‘chirish uchun kerakli kanal nomini bosing."
    )

    await callback.message.edit_text(
        text=text,
        parse_mode="HTML",
        reply_markup=delete_channels_list_keyboard(channels),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delete_channel_select:"), IsAdmin(admin_ids=ADMINS))
async def delete_selected_channel(callback: CallbackQuery):
    if not callback.message:
        await callback.answer()
        return

    try:
        channel_id = int(callback.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Noto‘g‘ri kanal ID", show_alert=True)
        return

    async with session_maker() as session:
        channel = await get_channel_by_id(session, channel_id)
        if not channel:
            await callback.answer("❌ Kanal topilmadi", show_alert=True)
            return

        # Soft delete
        result = await set_channel_active(
            session=session,
            channel_id=channel_id,
            is_active=False,
        )

    if not result:
        await callback.answer("❌ Kanalni o‘chirishda xatolik", show_alert=True)
        return

    await callback.message.edit_text(
        "✅ <b>Kanal o‘chirildi!</b>",
        parse_mode="HTML",
        reply_markup=delete_channel_success_keyboard(),
    )
    await callback.answer("Kanal o‘chirildi")