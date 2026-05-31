from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.filters.is_admin import IsAdmin
from app.keyboards.reply import admin_menu
from app.states.ads import AddAd
from app.keyboards.inline import (
    admin_ads,
    add_ad_actions,
    ads_list_keyboard,
    ad_detail_keyboard,
    delete_ads_keyboard,
    confirm_delete_ad_keyboard,
)
from data.config import ADMINS
from database.database import session_maker
from database.services.ads import (
    add_ad,
    get_all_ads,
    get_ad_by_id,
    delete_ad,
    set_ad_active,
)

router = Router()


def format_ad_text(ad) -> str:
    buttons = ad.buttons or []

    if buttons:
        buttons_text = "\n".join(
            f"• {btn.get('text', 'Tugma')} → {btn.get('url') or btn.get('callback_data', '-')}"
            for btn in buttons
        )
    else:
        buttons_text = "Tugmalar yo‘q"

    status = "🟢 Faol" if ad.is_active else "🔴 Faolsiz"

    return (
        "📢 <b>Reklama tafsilotlari</b>\n\n"
        f"🆔 <b>ID:</b> {ad.ad_id}\n"
        f"📌 <b>Sarlavha:</b> {ad.title or '—'}\n"
        f"📝 <b>Matn:</b> {ad.description or '—'}\n"
        f"📎 <b>Tugmalar:</b>\n{buttons_text}\n\n"
        f"📍 <b>Holati:</b> {status}\n"
        f"🗓 <b>Yaratilgan:</b> {ad.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
    )


@router.callback_query(F.data == "admin_ads", IsAdmin(admin_ids=ADMINS))
async def open_ads_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "📢 <b>Reklama bo‘limi</b>",
        parse_mode="HTML",
        reply_markup=admin_ads(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_add_ad", IsAdmin(admin_ids=ADMINS))
async def start_add_ad(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(AddAd.title)
    await state.update_data(buttons=[])
    await callback.message.edit_text("📢 Reklama sarlavhasini kiriting:")
    await callback.answer()


@router.message(AddAd.title, IsAdmin(admin_ids=ADMINS))
async def get_title(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("❌ Sarlavha matn bo‘lishi kerak.")
        return

    await state.update_data(title=message.text.strip())
    await state.set_state(AddAd.description)
    await message.answer("📝 Reklama matnini kiriting:")


@router.message(AddAd.description, IsAdmin(admin_ids=ADMINS))
async def get_description(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("❌ Matn yuboring.")
        return

    await state.update_data(description=message.text.strip())
    await state.set_state(AddAd.confirm_buttons)
    await message.answer(
        "🔘 Endi tugmalarni qo‘shing yoki reklamani saqlang:",
        reply_markup=add_ad_actions(),
    )


@router.callback_query(
    F.data == "add_button", AddAd.confirm_buttons, IsAdmin(admin_ids=ADMINS)
)
async def add_button_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddAd.waiting_for_button_text)
    await callback.message.edit_text("🔤 Tugma nomini kiriting:")
    await callback.answer()


@router.message(AddAd.waiting_for_button_text, IsAdmin(admin_ids=ADMINS))
async def get_button_text(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("❌ Tugma nomi matn bo‘lishi kerak.")
        return

    await state.update_data(current_button_text=message.text.strip())
    await state.set_state(AddAd.waiting_for_button_url_or_callback)
    await message.answer("🔗 Tugma uchun URL yoki callback_data kiriting:")


@router.message(AddAd.waiting_for_button_url_or_callback, IsAdmin(admin_ids=ADMINS))
async def get_button_data(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("❌ URL yoki callback_data yuboring.")
        return

    data = await state.get_data()
    button_text = data.get("current_button_text")
    button_data = message.text.strip()

    if not button_text:
        await state.set_state(AddAd.confirm_buttons)
        await message.answer("❌ Tugma nomi topilmadi. Qaytadan urinib ko‘ring.")
        return

    buttons = data.get("buttons", [])

    if button_data.startswith(("http://", "https://")):
        buttons.append({"text": button_text, "url": button_data})
    else:
        buttons.append({"text": button_text, "callback_data": button_data})

    await state.update_data(
        buttons=buttons,
        current_button_text=None,
    )
    await state.set_state(AddAd.confirm_buttons)

    btn_list = (
        "\n".join(
            f"• {btn['text']} → {btn.get('url') or btn.get('callback_data')}"
            for btn in buttons
        )
        or "Tugmalar yo‘q"
    )

    await message.answer(
        f"✅ Tugma qo‘shildi.\n\n{btn_list}",
        reply_markup=add_ad_actions(),
    )


@router.callback_query(
    F.data == "save_ad", AddAd.confirm_buttons, IsAdmin(admin_ids=ADMINS)
)
async def save_final_ad(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    title = data.get("title")
    description = data.get("description")
    buttons = data.get("buttons", [])

    if not title or not description:
        await callback.answer("❌ Ma'lumot yetarli emas", show_alert=True)
        return

    async with session_maker() as session:
        ad = await add_ad(
            session=session,
            title=title,
            description=description,
            buttons=buttons,
        )

    if not ad:
        await callback.answer("❌ Reklama saqlanmadi", show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text(
        "✅ <b>Reklama muvaffaqiyatli saqlandi.</b>",
        parse_mode="HTML",
        reply_markup=admin_ads(),
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_add_ad", IsAdmin(admin_ids=ADMINS))
async def cancel_add_ad(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "📢 <b>Reklama bo‘limi</b>",
        parse_mode="HTML",
        reply_markup=admin_ads(),
    )
    await callback.answer("Bekor qilindi")


@router.callback_query(F.data == "admin_ads_list", IsAdmin(admin_ids=ADMINS))
async def show_ads_list(callback: CallbackQuery):
    async with session_maker() as session:
        ads = await get_all_ads(session)

    if not ads:
        await callback.message.edit_text(
            "📋 Reklamalar topilmadi.",
            reply_markup=admin_ads(),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "📋 <b>Reklamalar ro‘yxati</b>",
        parse_mode="HTML",
        reply_markup=ads_list_keyboard(ads),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("view_ad:"), IsAdmin(admin_ids=ADMINS))
async def view_ad(callback: CallbackQuery):
    ad_id_raw = callback.data.split(":", 1)[1]

    if not ad_id_raw.isdigit():
        await callback.answer("❌ Noto‘g‘ri ID", show_alert=True)
        return

    ad_id = int(ad_id_raw)

    async with session_maker() as session:
        ad = await get_ad_by_id(session, ad_id)

    if not ad:
        await callback.answer("❌ Reklama topilmadi", show_alert=True)
        return

    await callback.message.edit_text(
        format_ad_text(ad),
        parse_mode="HTML",
        reply_markup=ad_detail_keyboard(ad.ad_id, ad.is_active),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("toggle_ad:"), IsAdmin(admin_ids=ADMINS))
async def toggle_ad_status(callback: CallbackQuery):
    ad_id_raw = callback.data.split(":", 1)[1]

    if not ad_id_raw.isdigit():
        await callback.answer("❌ Noto‘g‘ri ID", show_alert=True)
        return

    ad_id = int(ad_id_raw)

    async with session_maker() as session:
        ad = await get_ad_by_id(session, ad_id)
        if not ad:
            await callback.answer("❌ Reklama topilmadi", show_alert=True)
            return

        updated = await set_ad_active(
            session=session,
            ad_id=ad_id,
            is_active=not ad.is_active,
        )

    if not updated:
        await callback.answer("❌ Holatni o‘zgartirib bo‘lmadi", show_alert=True)
        return

    await callback.message.edit_text(
        format_ad_text(updated),
        parse_mode="HTML",
        reply_markup=ad_detail_keyboard(updated.ad_id, updated.is_active),
    )
    await callback.answer("Holat o‘zgartirildi")


@router.callback_query(F.data == "admin_delete_ad", IsAdmin(admin_ids=ADMINS))
async def delete_ad_menu(callback: CallbackQuery):
    async with session_maker() as session:
        ads = await get_all_ads(session)

    if not ads:
        await callback.message.edit_text(
            "🗑 o‘chirish uchun reklama topilmadi.",
            reply_markup=admin_ads(),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "🗑 <b>o‘chirish uchun reklamani tanlang</b>",
        parse_mode="HTML",
        reply_markup=delete_ads_keyboard(ads),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delete_ad:"), IsAdmin(admin_ids=ADMINS))
async def delete_ad_confirm(callback: CallbackQuery):
    ad_id_raw = callback.data.split(":", 1)[1]

    if not ad_id_raw.isdigit():
        await callback.answer("❌ Noto‘g‘ri ID", show_alert=True)
        return

    ad_id = int(ad_id_raw)

    async with session_maker() as session:
        ad = await get_ad_by_id(session, ad_id)

    if not ad:
        await callback.answer("❌ Reklama topilmadi", show_alert=True)
        return

    await callback.message.edit_text(
        f"⚠️ <b>“{ad.title or 'Nomsiz reklama'}”</b> reklamasini o‘chirmoqchimisiz?",
        parse_mode="HTML",
        reply_markup=confirm_delete_ad_keyboard(ad.ad_id),
    )
    await callback.answer()


@router.callback_query(
    F.data.startswith("confirm_delete_ad:"), IsAdmin(admin_ids=ADMINS)
)
async def delete_ad_handler(callback: CallbackQuery):
    ad_id_raw = callback.data.split(":", 1)[1]

    if not ad_id_raw.isdigit():
        await callback.answer("❌ Noto‘g‘ri ID", show_alert=True)
        return

    ad_id = int(ad_id_raw)

    async with session_maker() as session:
        deleted = await delete_ad(session, ad_id)

    if not deleted:
        await callback.answer("❌ Reklama topilmadi", show_alert=True)
        return

    await callback.message.edit_text(
        "✅ Reklama o‘chirildi.",
        reply_markup=admin_ads(),
    )
    await callback.answer()
