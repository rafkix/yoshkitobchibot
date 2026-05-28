from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.models import Channel


# =========================
# 🔐 ADMIN: CHANNEL
# =========================

async def admin_channel() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(text="➕ Kanal qo‘shish", callback_data="add_channel")
    builder.button(text="📊 Kanallar soni", callback_data="count_channels")
    builder.button(text="🗑 Kanalni o‘chirish", callback_data="delete_channels")

    builder.adjust(1)
    return builder.as_markup()


def admin_channels_list_keyboard(channels: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for channel in channels:
        title = channel.title or channel.channel_link or f"Kanal #{channel.channel_id}"
        title = title[:45] + "..." if len(title) > 45 else title

        builder.button(
            text=f"⚙️ {title}",
            callback_data=f"admin_view_channel:{channel.channel_id}",
        )

    builder.button(text="⏪ Orqaga", callback_data="admin_channel")
    builder.adjust(1)
    return builder.as_markup()


def admin_channel_detail_keyboard(channel) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if channel.channel_link:
        builder.button(text="↗️ Kanalga o‘tish", url=channel.channel_link)

    builder.button(text="⏪ Orqaga", callback_data="count_channels")

    builder.adjust(1)
    return builder.as_markup()


# =========================
# 🗑 DELETE FLOW
# =========================

def delete_channels_list_keyboard(channels: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for channel in channels:
        title = channel.title or channel.channel_link or f"Kanal #{channel.channel_id}"
        title = title[:40] + "..." if len(title) > 40 else title

        builder.button(
            text=f"🗑 {title}",
            callback_data=f"delete_channel_select:{channel.channel_id}",
        )

    builder.button(text="⏪ Orqaga", callback_data="admin_channel")
    builder.adjust(1)
    return builder.as_markup()


def delete_channel_success_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⏪ Orqaga", callback_data="admin_channel")
    builder.adjust(1)
    return builder.as_markup()


# =========================
# ⚙️ CHANNEL TYPE
# =========================

def channel_type_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(
        text="📢 Ommaviy / Shaxsiy (Kanal · Guruh)",
        callback_data="channel_type:telegram_channel",
    )
    builder.button(
        text="🔐 Shaxsiy / So‘rovli havola",
        callback_data="channel_type:telegram_invite",
    )
    builder.button(
        text="🌐 Oddiy havola",
        callback_data="channel_type:external_link",
    )
    builder.button(text="⬅️ Orqaga", callback_data="admin_channel")

    builder.adjust(1)
    return builder.as_markup()


def cancel_channel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="cancel_add_channel")]
        ]
    )


# =========================
# 📢 ADS
# =========================


def admin_ads() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(text="➕ Reklama qo‘shish", callback_data="admin_add_ad")
    builder.button(text="📋 Reklamalar ro‘yxati", callback_data="admin_ads_list")
    builder.button(text="🗑 Reklama o‘chirish", callback_data="admin_delete_ad")

    builder.adjust(1)
    return builder.as_markup()


def add_ad_actions() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(text="➕ Tugma qo‘shish", callback_data="add_button")
    builder.button(text="✅ Reklamani saqlash", callback_data="save_ad")
    builder.button(text="❌ Bekor qilish", callback_data="cancel_add_ad")

    builder.adjust(1)
    return builder.as_markup()


def ads_list_keyboard(ads: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for ad in ads:
        title = (ad.title or "Nomsiz reklama").strip()
        if len(title) > 40:
            title = title[:37] + "..."

        status = "🟢" if ad.is_active else "🔴"
        builder.button(
            text=f"{status} {title}",
            callback_data=f"view_ad:{ad.ad_id}",
        )

    builder.button(text="⬅️ Orqaga", callback_data="admin_ads")
    builder.adjust(1)
    return builder.as_markup()


def ad_detail_keyboard(ad_id: int, is_active: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(
        text="🔴 Faolsiz qilish" if is_active else "🟢 Faollashtirish",
        callback_data=f"toggle_ad:{ad_id}",
    )
    builder.button(
        text="🗑 O‘chirish",
        callback_data=f"delete_ad:{ad_id}",
    )
    builder.button(
        text="⬅️ Orqaga",
        callback_data="admin_ads_list",
    )

    builder.adjust(1)
    return builder.as_markup()


def delete_ads_keyboard(ads: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for ad in ads:
        title = (ad.title or "Nomsiz reklama").strip()
        if len(title) > 40:
            title = title[:37] + "..."

        builder.button(
            text=f"🗑 {title}",
            callback_data=f"delete_ad:{ad.ad_id}",
        )

    builder.button(text="⬅️ Orqaga", callback_data="admin_ads")
    builder.adjust(1)
    return builder.as_markup()


def confirm_delete_ad_keyboard(ad_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(text="✅ Ha, o‘chirish", callback_data=f"confirm_delete_ad:{ad_id}")
    builder.button(text="⬅️ Bekor qilish", callback_data=f"view_ad:{ad_id}")

    builder.adjust(1)
    return builder.as_markup()

def admin_ads_send() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(text="✉️ Oddiy", callback_data="admin_send_copy")
    builder.button(text="📨 Forward", callback_data="admin_send_forward")

    builder.adjust(2)
    return builder.as_markup()

def cancel_ads_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="cancel_add_ads")]
        ]
    )


def build_ad_buttons(buttons: list) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(**btn)] for btn in buttons]
    )


def back_to_main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Asosiy menyu", callback_data="back_menu")
    return builder.as_markup()
