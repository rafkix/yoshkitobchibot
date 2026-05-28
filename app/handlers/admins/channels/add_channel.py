from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from app.filters.is_admin import IsAdmin
from app.keyboards.inline import (
    channel_type_keyboard,
    cancel_channel_keyboard,
    admin_channel,
)
from app.keyboards.reply import admin_menu
from app.states.add_channel import AddChannelState
from data.config import ADMINS
from database.database import session_maker
from database.services.channel_service import add_channel

router = Router()


CHANNEL_TYPE_TEXT = """<b>⚙️ Majburiy obuna turini tanlang:</b>

Quyida majburiy obunani qo‘shishning 3 ta turi mavjud:

<blockquote>🔹 Ommaviy / Shaxsiy (Kanal · Guruh)
Har qanday kanal yoki guruhni (ommaviy yoki shaxsiy) majburiy obunaga ulash.

🔹 Shaxsiy / So‘rovli havola
Shaxsiy yoki so‘rovli kanal/guruh havolasi orqali o‘tganlarni kuzatish.

🔹 🌐 Oddiy havola
Majburiy tekshiruvsiz oddiy havolani ko‘rsatish (Instagram, sayt va boshqalar).</blockquote>"""

TELEGRAM_CHANNEL_TEXT = """<b>📢 Ommaviy / Shaxsiy (Kanal · Guruh) - ulash</b>

Quyida kanal/guruhni ulashning 3 ta oddiy usuli mavjud:

<blockquote>🔹 1. ID orqali ulash
Kanal yoki guruh ID raqamini kiriting.
ID odatda -100... shaklida bo‘ladi.

🔹 2. Havola orqali ulash
Kanal/guruh havolasini yuboring.
Masalan: <code>@kanal_nomi</code> yoki <code>https://t.me/kanal</code>

🔹 3. Postni ulash orqali
Kanal yoki guruhdan bitta postni ulashing va shu xabarni botga yuboring.
Bot avtomatik ravishda kanalni taniydi.</blockquote>"""

PRIVATE_SOURCE_TEXT = """<b>🔐 Shaxsiy / So‘rovli havola - ulash</b>

Quyida kanal/guruhni ulashning 3 ta oddiy usuli mavjud:

<blockquote>🔹 1. ID orqali ulash
Kanal yoki guruh ID raqamini kiriting.
ID odatda -100... shaklida bo‘ladi.

🔹 2. Havola orqali ulash
Kanal/guruh havolasini yuboring.
Masalan: <code>@kanal_nomi</code> yoki <code>https://t.me/kanal</code>

🔹 3. Postni ulash orqali
Kanal yoki guruhdan bitta postni ulashing va shu xabarni botga yuboring.
Bot avtomatik ravishda kanalni taniydi.</blockquote>
"""

EXTERNAL_LINK_TEXT = """🔗 Havola kiriting:

Masalan: <code>https://site.com</code> yoki <code>https://t.me/kanal</code>

Iltimos, yuqoridagi kabi to‘g‘ri formatda havolani kiriting."""

TYPE_LABELS = {
    "telegram_channel": "📢 Ommaviy / Shaxsiy (Kanal · Guruh)",
    "telegram_invite": "🔐 Shaxsiy / So‘rovli havola",
    "external_link": "🌐 Oddiy havola",
}


def normalize_public_link(link: str) -> str:
    link = link.strip()

    if link.startswith("@"):
        return f"https://t.me/{link[1:]}"
    if link.startswith("t.me/"):
        return f"https://{link}"
    if link.startswith("http://t.me/"):
        return link.replace("http://", "https://", 1)

    return link


def is_telegram_chat_id(value: str) -> bool:
    value = value.strip()
    return value.startswith("-100") and value[1:].isdigit()


def is_public_telegram_link(value: str) -> bool:
    value = value.strip()
    return (
        (
            value.startswith("@")
            or value.startswith("https://t.me/")
            or value.startswith("http://t.me/")
            or value.startswith("t.me/")
        )
        and "/+" not in value
        and "joinchat" not in value
    )


def is_private_telegram_link(value: str) -> bool:
    value = value.strip()
    return (
        value.startswith("https://t.me/+")
        or value.startswith("http://t.me/+")
        or "joinchat" in value
    )


def is_external_url(value: str) -> bool:
    value = value.strip()
    return value.startswith("http://") or value.startswith("https://")


def build_selected_type_text(link_type: str) -> str:
    if link_type == "telegram_channel":
        body = TELEGRAM_CHANNEL_TEXT
    elif link_type == "telegram_invite":
        body = PRIVATE_SOURCE_TEXT
    elif link_type == "external_link":
        body = EXTERNAL_LINK_TEXT
    else:
        body = CHANNEL_TYPE_TEXT

    return f"{body}"


@router.message(F.text == "🔐 Kanallar", IsAdmin(admin_ids=ADMINS))
async def open_channels_section(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🔐 Majburiy obuna kanallar:",
        reply_markup=await admin_channel(),
    )


@router.callback_query(F.data == "add_channel", IsAdmin(admin_ids=ADMINS))
async def start_add_channel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        CHANNEL_TYPE_TEXT,
        parse_mode="HTML",
        reply_markup=channel_type_keyboard(),
        disable_web_page_preview=True,
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_add_channel", IsAdmin(admin_ids=ADMINS))
async def cancel_add_channel_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        CHANNEL_TYPE_TEXT,
        parse_mode="HTML",
        reply_markup=channel_type_keyboard(),
    )
    await callback.answer("Bekor qilindi")


@router.callback_query(F.data == "admin_channel", IsAdmin(admin_ids=ADMINS))
async def back_to_admin_channel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "🔐 Majburiy obuna kanallar:",
        reply_markup=await admin_channel(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("channel_type:"), IsAdmin(admin_ids=ADMINS))
async def select_channel_type(callback: CallbackQuery, state: FSMContext):
    link_type = callback.data.split(":", 1)[1]
    await state.update_data(link_type=link_type)

    text = build_selected_type_text(link_type)

    if link_type == "external_link":
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=cancel_channel_keyboard(),
            disable_web_page_preview=True,
        )
        await state.set_state(AddChannelState.waiting_for_external_link)
        await callback.answer()
        return

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=cancel_channel_keyboard(),
    )
    await state.set_state(AddChannelState.waiting_for_source)
    await callback.answer()


@router.message(
    AddChannelState.waiting_for_source,
    F.text.casefold() == "cancel",
    IsAdmin(admin_ids=ADMINS),
)
@router.message(
    AddChannelState.waiting_for_private_link,
    F.text.casefold() == "cancel",
    IsAdmin(admin_ids=ADMINS),
)
@router.message(
    AddChannelState.waiting_for_external_link,
    F.text.casefold() == "cancel",
    IsAdmin(admin_ids=ADMINS),
)
@router.message(
    AddChannelState.waiting_for_external_title,
    F.text.casefold() == "cancel",
    IsAdmin(admin_ids=ADMINS),
)
async def cancel_channel_by_text(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "❌ Bekor qilindi.",
        reply_markup=admin_menu(),
    )


@router.message(AddChannelState.waiting_for_source, IsAdmin(admin_ids=ADMINS))
async def process_telegram_source(message: Message, state: FSMContext):
    data = await state.get_data()
    link_type = data.get("link_type")

    if not link_type:
        await state.clear()
        await message.answer(
            "❗ Avval kanal turini tanlang.",
            reply_markup=admin_menu(),
        )
        return

    telegram_chat_id: int | None = None
    channel_link: str | None = None
    title: str | None = None

    if message.forward_from_chat:
        chat = message.forward_from_chat
        telegram_chat_id = chat.id
        title = chat.title

        if chat.username:
            channel_link = f"https://t.me/{chat.username}"

    else:
        raw_text = (message.text or "").strip()

        if is_telegram_chat_id(raw_text):
            telegram_chat_id = int(raw_text)

        elif is_public_telegram_link(raw_text):
            channel_link = normalize_public_link(raw_text)

            try:
                chat = await message.bot.get_chat(channel_link)
                telegram_chat_id = chat.id
                title = getattr(chat, "title", None)

                if getattr(chat, "username", None):
                    channel_link = f"https://t.me/{chat.username}"
            except Exception:
                await message.answer(
                    "❗ Bu havola orqali kanal yoki guruhni aniqlab bo‘lmadi.\n\n"
                    "Quyidagilardan birini yuboring:\n"
                    "• <code>-100...</code> ID\n"
                    "• <code>@kanal_nomi</code>\n"
                    "• <code>https://t.me/kanal</code>\n"
                    "• yoki forward qilingan post",
                    parse_mode="HTML",
                    reply_markup=cancel_channel_keyboard(),
                    disable_web_page_preview=True,
                )
                return

        else:
            await message.answer(
                "❗ Noto‘g‘ri format.\n\n"
                "Yuboring:\n"
                "• <code>-100...</code> ko‘rinishidagi Telegram ID\n"
                "• <code>@kanal_nomi</code> yoki <code>https://t.me/kanal</code>\n"
                "• yoki forward qilingan post",
                parse_mode="HTML",
                reply_markup=cancel_channel_keyboard(),
                disable_web_page_preview=True,
            )
            return

    if telegram_chat_id is None:
        await message.answer(
            "❗ Telegram chat ID aniqlanmadi.",
            reply_markup=cancel_channel_keyboard(),
        )
        return

    if link_type == "telegram_invite":
        await state.update_data(
            telegram_chat_id=telegram_chat_id,
            title=title,
            public_link=channel_link,
        )
        await message.answer(
            EXTERNAL_LINK_TEXT,
            parse_mode="HTML",
            reply_markup=cancel_channel_keyboard(),
            disable_web_page_preview=True,
        )
        await state.set_state(AddChannelState.waiting_for_private_link)
        return

    async with session_maker() as session:
        channel = await add_channel(
            session=session,
            title=title,
            telegram_chat_id=telegram_chat_id,
            channel_link=channel_link,
            link_type="telegram_channel",
            is_private=False,
            requires_check=True,
        )

    if not channel:
        await message.answer(
            "❌ Bu kanal allaqachon mavjud yoki qo‘shishda xatolik bo‘ldi.",
            reply_markup=admin_menu(),
        )
    else:
        await message.answer(
            f"✅ Kanal qo‘shildi.\n\n"
            f"🆔 Telegram ID: <code>{telegram_chat_id}</code>\n"
            f"📌 Nomi: {title or 'Noma’lum'}\n"
            f"🔗 Havola: {channel_link or 'Bot aniqlamadi'}\n"
            f"📂 Turi: {TYPE_LABELS['telegram_channel']}",
            parse_mode="HTML",
            reply_markup=admin_menu(),
            disable_web_page_preview=True,
        )

    await state.clear()


@router.message(
    AddChannelState.waiting_for_private_link,
    F.text,
    IsAdmin(admin_ids=ADMINS),
)
async def process_private_link(message: Message, state: FSMContext):
    invite_link = (message.text or "").strip()

    if not is_private_telegram_link(invite_link):
        await message.answer(
            "❗ To‘g‘ri private invite link yuboring.\n\n"
            "Masalan:\n"
            "<code>https://t.me/+xxxxxx</code>\n"
            "yoki <code>https://t.me/joinchat/xxxxxx</code>",
            parse_mode="HTML",
            reply_markup=cancel_channel_keyboard(),
            disable_web_page_preview=True,
        )
        return

    data = await state.get_data()
    telegram_chat_id = data.get("telegram_chat_id")
    title = data.get("title")

    if telegram_chat_id is None:
        await state.clear()
        await message.answer(
            "❗ Avval kanal manbasini yuboring.",
            reply_markup=admin_menu(),
        )
        return

    async with session_maker() as session:
        channel = await add_channel(
            session=session,
            title=title,
            telegram_chat_id=telegram_chat_id,
            channel_link=invite_link,
            link_type="telegram_invite",
            is_private=True,
            requires_check=True,
        )

    if not channel:
        await message.answer(
            "❌ Bu kanal allaqachon mavjud yoki qo‘shishda xatolik bo‘ldi.",
            reply_markup=admin_menu(),
        )
    else:
        await message.answer(
            f"✅ Private kanal qo‘shildi.\n\n"
            f"🆔 Telegram ID: <code>{telegram_chat_id}</code>\n"
            f"📌 Nomi: {title or 'Noma’lum'}\n"
            f"🔗 Invite link saqlandi\n"
            f"📂 Turi: {TYPE_LABELS['telegram_invite']}",
            parse_mode="HTML",
            reply_markup=admin_menu(),
            disable_web_page_preview=True,
        )

    await state.clear()


@router.message(
    AddChannelState.waiting_for_external_link,
    F.text,
    IsAdmin(admin_ids=ADMINS),
)
async def process_external_link(message: Message, state: FSMContext):
    link = (message.text or "").strip()

    if not is_external_url(link):
        await message.answer(
            "❗ To‘g‘ri havola yuboring.\n\nMasalan: <code>https://site.com</code>",
            parse_mode="HTML",
            reply_markup=cancel_channel_keyboard(),
            disable_web_page_preview=True,
        )
        return

    await state.update_data(channel_link=link)
    await message.answer(
        "📝 Bu havola uchun nom kiriting:",
        reply_markup=cancel_channel_keyboard(),
    )
    await state.set_state(AddChannelState.waiting_for_external_title)


@router.message(
    AddChannelState.waiting_for_external_title,
    F.text,
    IsAdmin(admin_ids=ADMINS),
)
async def process_external_link_title(message: Message, state: FSMContext):
    title = message.text.strip()

    if len(title) < 2:
        await message.answer(
            "❗ Nom juda qisqa.",
            reply_markup=cancel_channel_keyboard(),
        )
        return

    data = await state.get_data()
    link = data.get("channel_link")

    if not link:
        await state.clear()
        await message.answer(
            "❗ Avval havolani yuboring.",
            reply_markup=admin_menu(),
        )
        return

    async with session_maker() as session:
        channel = await add_channel(
            session=session,
            title=title,
            telegram_chat_id=None,
            channel_link=link,
            link_type="external_link",
            is_private=False,
            requires_check=False,
        )

    if not channel:
        await message.answer(
            "❌ Bu havola allaqachon mavjud yoki qo‘shishda xatolik bo‘ldi.",
            reply_markup=admin_menu(),
        )
    else:
        await message.answer(
            f"✅ Oddiy havola qo‘shildi.\n\n"
            f"📝 Nomi: {title}\n"
            f"🔗 Havola: {link}\n"
            f"📂 Turi: {TYPE_LABELS['external_link']}",
            reply_markup=admin_menu(),
            disable_web_page_preview=True,
        )

    await state.clear()
