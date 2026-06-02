from aiogram import Router, F
from aiogram.types import CallbackQuery

from app.filters.is_admin import IsAdmin
from app.keyboards.inline import (
    admin_channel,
    admin_channels_list_keyboard,
    admin_channel_detail_keyboard,
)
from data.config import ADMINS
from database.models import Channel
from database.services.channel_service import ChannelService
from database.database import session_maker

router = Router()


def format_channel_type(link_type: str) -> str:
    mapping = {
        "telegram_channel": "📢 Telegram kanal/guruh",
        "telegram_invite": "🔐 Private / so‘rovli havola",
        "external_link": "🌐 Oddiy havola",
    }
    return mapping.get(link_type, link_type)


def format_channel_title(channel) -> str:
    return channel.title or channel.channel_link or f"Kanal #{channel.channel_id}"


@router.callback_query(F.data == "count_channels", IsAdmin(admin_ids=ADMINS))
async def show_channels_list(callback: CallbackQuery):
    if not callback.message:
        await callback.answer()
        return

    async with session_maker() as session:
        total = await ChannelService.count_channels(session)
        channels = await ChannelService.get_all_channels(session)

    text = (
        "📋 <b>Majburiy obuna kanallari ro‘yxati:</b>\n\n"
        f"🔢 <b>Jami:</b> {total} ta\n\n"
        "👇 Kerakli kanal ustiga bosib ma'lumotlarini ko‘rishingiz mumkin"
    )

    await callback.message.edit_text(
        text=text,
        parse_mode="HTML",
        reply_markup=admin_channels_list_keyboard(channels),
    )
    await callback.answer()


@router.callback_query(
    F.data.startswith("admin_view_channel:"), IsAdmin(admin_ids=ADMINS)
)
async def show_channel_detail(callback: CallbackQuery):
    if not callback.message:
        await callback.answer()
        return

    try:
        channel_id = int(callback.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Noto‘g‘ri kanal ID", show_alert=True)
        return

    async with session_maker() as session:
        channel = await ChannelService.get_channel_by_id(session, channel_id)

        if not channel:
            await callback.answer("❌ Kanal topilmadi", show_alert=True)
            return

        # Telegram kanal/guruh/private invite bo‘lsa real obunachilar sonini olib ko‘ramiz
        if (
            channel.link_type in {"telegram_channel", "telegram_invite"}
            and channel.channel_id
        ):
            try:
                real_count = await callback.bot.get_chat_member_count(
                    channel.channel_id
                )

                updated_channel = await ChannelService.update_channel_subscribers(
                    session=session,
                    channel_id=channel.channel_id,
                    new_count=real_count,
                )

                if updated_channel:
                    channel = updated_channel

            except Exception:
                # Agar Telegram API dan olib bo‘lmasa,
                # bazadagi eski qiymatlar bilan davom etamiz
                pass

        current_count = channel.current_subscribers_count or 0

    text = (
        "🏳️ <b>Kanal tafsilotlari</b>\n\n"
        f"📌 <b>Nomi:</b> <i>{format_channel_title(channel)}</i>\n"
        f"👥 <b>Obunachilar:</b> {current_count} ta\n"
        f"🗓 <b>Qo‘shilgan:</b> {channel.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    await callback.message.edit_text(
        text=text,
        parse_mode="HTML",
        reply_markup=admin_channel_detail_keyboard(channel),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_channel", IsAdmin(admin_ids=ADMINS))
async def back_to_admin_channels(callback: CallbackQuery):
    if not callback.message:
        await callback.answer()
        return

    await callback.message.edit_text(
        text="🔐 Majburiy obuna kanallar:",
        reply_markup=await admin_channel(),
    )
    await callback.answer()
