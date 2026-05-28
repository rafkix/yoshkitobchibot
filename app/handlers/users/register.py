# app/handlers/users/register.py

from datetime import datetime

from aiogram import Router, F
from aiogram.types import (
    Message,
    Contact,
    ReplyKeyboardRemove,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext

from database.models import ContestType, DirectionType
from database.services.user_service import UserService
from database.database import session_maker

from app.states.register import RegisterState

from app.keyboards.reply import (
    regions_keyboard,
    districts_keyboard,
    mahallas_keyboard,
    contact_keyboard,
    contest_keyboard,
    direction_keyboard,
    main_menu_keyboard,
    regions_data,
    districts_data,
    mahallas_data,
)

router = Router()


# =========================================================
# HELPERS
# =========================================================

CONTEST_LABELS = {
    ContestType.YOSH_KITOBXON_2026: "\u201cYosh kitobxon\u201d tanlovi 2026",
}

DIRECTION_LABELS = {
    DirectionType.AGE_10_14: "10-14 yosh toifasi",
    DirectionType.AGE_15_19: "15-19 yosh toifasi",
    DirectionType.AGE_20_30: "20-30 yosh toifasi (1996-2006)",
}

CONTEST_MAPPING = {
    "\u201cYosh kitobxon\u201d tanlovi 2026": ContestType.YOSH_KITOBXON_2026,
}

DIRECTION_MAPPING = {
    "10-14 yosh toifasi (2012-2016)": DirectionType.AGE_10_14,
    "15-19 yosh toifasi (2007-2011)": DirectionType.AGE_15_19,
    "20-30 yosh toifasi (1996-2006)": DirectionType.AGE_20_30,
}


def edit_fields_keyboard() -> InlineKeyboardMarkup:
    """Confirm sahifasida har bir maydon uchun tahrirlash tugmalari."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="F.I.Sh o‘zgartirish", callback_data="edit:full_name"
                ),
                InlineKeyboardButton(
                    text="Tug‘ilgan sana o‘zgartirish",
                    callback_data="edit:birth_date",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Hudud o‘zgartirish", callback_data="edit:region"
                ),
                InlineKeyboardButton(
                    text="Tuman o‘zgartirish", callback_data="edit:district"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Mahalla o‘zgartirish", callback_data="edit:neighborhood"
                ),
                InlineKeyboardButton(
                    text="Ish/o‘qish joyi o‘zgartirish",
                    callback_data="edit:workplace",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Telefon o‘zgartirish", callback_data="edit:phone"
                ),
                InlineKeyboardButton(
                    text="Tanlov/yo‘nalish o‘zgartirish",
                    callback_data="edit:contest",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="\u2705 Tasdiqlash", callback_data="confirm:yes"
                ),
            ],
        ]
    )


async def show_confirm(message: Message, state: FSMContext):
    """Confirm xabarini ko‘rsatish."""
    data = await state.get_data()

    text = (
        "<b>Ma'lumotlaringizni tasdiqlang:</b>\n\n"
        f"<b>F.I.Sh:</b> {data['full_name']}\n"
        f"<b>Tug‘ilgan sana:</b> {data['birth_date']}\n"
        f"<b>Yashash joyi:</b> {data['region']}, {data['district']}, {data['neighborhood']}\n"
        f"<b>Ish/o‘qish:</b> {data['workplace']}\n"
        f"<b>Telefon:</b> <code>{data['phone_number']}</code>\n\n"
        f"<b>Tanlov:</b> {CONTEST_LABELS[data['contest']]}\n"
        f"<b>Yo‘nalish:</b> {DIRECTION_LABELS[data['direction']]}\n\n"
        "<i>Tahrirlash uchun tegishli tugmani bosing.</i>"
    )

    await state.set_state(RegisterState.confirm)
    await message.answer(text, reply_markup=edit_fields_keyboard())


def is_editing(data: dict) -> bool:
    """Foydalanuvchi allaqachon ro‘yxatdan o‘tishni yakunlagan (tahrirlash rejimi)."""
    return bool(data.get("contest") and data.get("direction"))


def find_mahalla(district_id: int, text: str) -> dict | None:
    """
    Foydalanuvchi bosgan tugma matni bo‘yicha mahallani topadi.
    Tugmada mfy_name ko‘rsatiladi (masalan "Bo‘ston MFY"),
    shuning uchun ham mfy_name, ham name bilan solishtiradi.
    """
    for m in mahallas_data:
        if int(m["district_id"]) != int(district_id):
            continue
        if m.get("mfy_name") == text or m["name"] == text:
            return m
    return None


# =========================================================
# START REGISTRATION
# =========================================================


@router.message(F.text == "📝 Ro‘yxatdan o‘tish")
async def start_registration(message: Message, state: FSMContext):
    await state.set_state(RegisterState.full_name)
    await message.answer(
        "<b>Familiya, ism va sharifingizni kiriting.</b>\n"
        "<i>(Abdullayev Abdullajon Abdulla o‘g‘li)</i>",
        reply_markup=ReplyKeyboardRemove(),
    )


# =========================================================
# FULL NAME
# =========================================================


@router.message(RegisterState.full_name)
async def process_full_name(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    data = await state.get_data()

    if is_editing(data):
        return await show_confirm(message, state)

    await state.set_state(RegisterState.birth_date)
    await message.answer(
        "<b>Tug‘ilgan sana va yilingizni kiriting.</b>\n<i>(Namuna: 31.01.2010)</i>",
        reply_markup=ReplyKeyboardRemove(),
    )


# =========================================================
# BIRTH DATE
# =========================================================


@router.message(RegisterState.birth_date)
async def process_birth_date(message: Message, state: FSMContext):
    try:
        birth_date = datetime.strptime(message.text, "%d.%m.%Y").date()
    except ValueError:
        return await message.answer(
            "<b>Sana noto‘g‘ri formatda.</b>\n\n<i>(Namuna: 31.01.2010)</i>"
        )

    await state.update_data(birth_date=birth_date)
    data = await state.get_data()

    if is_editing(data):
        return await show_confirm(message, state)

    await state.set_state(RegisterState.region)
    await message.answer(
        "<b>Hududingizni tanlang.</b>",
        reply_markup=regions_keyboard(),
    )


# =========================================================
# REGION
# =========================================================


@router.message(RegisterState.region)
async def process_region(message: Message, state: FSMContext):
    selected = next((r for r in regions_data if r["name"] == message.text), None)

    if not selected:
        return await message.answer(
            "<i>Hududni tugmalar orqali tanlang.</i>",
            reply_markup=regions_keyboard(),
        )

    await state.update_data(
        region=selected["name"],
        region_id=selected["id"],
        district=None,
        district_id=None,
        neighborhood=None,
    )

    await state.set_state(RegisterState.district)
    await message.answer(
        "<b>Tuman/shaharni tanlang.</b>",
        reply_markup=districts_keyboard(selected["id"]),
    )


# =========================================================
# DISTRICT
# =========================================================


@router.message(RegisterState.district, F.text == "⬅️ Orqaga")
async def back_to_region(message: Message, state: FSMContext):
    await state.set_state(RegisterState.region)
    await message.answer(
        "<b>Hududingizni tanlang.</b>",
        reply_markup=regions_keyboard(),
    )


@router.message(RegisterState.district)
async def process_district(message: Message, state: FSMContext):
    data = await state.get_data()
    region_id = data["region_id"]

    selected = next(
        (
            d
            for d in districts_data
            if int(d["region_id"]) == int(region_id) and d["name"] == message.text
        ),
        None,
    )

    if not selected:
        return await message.answer(
            "<i>Tumanni tugmalar orqali tanlang.</i>",
            reply_markup=districts_keyboard(region_id),
        )

    await state.update_data(
        district=selected["name"],
        district_id=selected["id"],
        neighborhood=None,
    )

    await state.set_state(RegisterState.neighborhood)
    await message.answer(
        "<b>Mahallani tanlang.</b>",
        reply_markup=mahallas_keyboard(selected["id"]),
    )


# =========================================================
# NEIGHBORHOOD
# =========================================================


@router.message(RegisterState.neighborhood, F.text == "⬅️ Orqaga")
async def back_to_district(message: Message, state: FSMContext):
    data = await state.get_data()
    region_id = data.get("region_id")
    await state.set_state(RegisterState.district)
    await message.answer(
        "<b>Tuman/shaharni tanlang.</b>",
        reply_markup=districts_keyboard(region_id) if region_id else regions_keyboard(),
    )


@router.message(RegisterState.neighborhood)
async def process_neighborhood(message: Message, state: FSMContext):
    data = await state.get_data()
    district_id = data["district_id"]

    # mfy_name ("Bo‘ston MFY") yoki name ("Bo‘ston") — ikkalasi bilan qidiriladi
    selected = find_mahalla(district_id, message.text)

    if not selected:
        await state.set_state(RegisterState.neighborhood_manual)
        return await message.answer(
            "<i>Mahalla ro‘yxatda topilmadi.</i>\n\n"
            "<b>Mahalla nomini o‘zingiz kiriting:</b>",
            reply_markup=ReplyKeyboardRemove(),
        )

    # Saqlanayotganda mfy_name emas, name saqlanadi
    await state.update_data(neighborhood=selected["name"])
    data = await state.get_data()

    if is_editing(data):
        return await show_confirm(message, state)

    await state.set_state(RegisterState.workplace)
    await message.answer(
        "<b>o‘qish yoki ish joyingizni kiriting.</b>\n"
        "<i>(Namuna: Talaba, o‘zMU 2-kurs)</i>",
        reply_markup=ReplyKeyboardRemove(),
    )


# =========================================================
# NEIGHBORHOOD MANUAL
# =========================================================


@router.message(RegisterState.neighborhood_manual)
async def process_neighborhood_manual(message: Message, state: FSMContext):
    if not message.text or len(message.text.strip()) < 2:
        return await message.answer(
            "<i>Mahalla nomi juda qisqa. Iltimos, to‘liq kiriting.</i>"
        )

    await state.update_data(neighborhood=message.text.strip())
    data = await state.get_data()

    if is_editing(data):
        return await show_confirm(message, state)

    await state.set_state(RegisterState.workplace)
    await message.answer(
        "<b>o‘qish yoki ish joyingizni kiriting.</b>\n"
        "<i>(Namuna: Talaba, o‘zMU 2-kurs)</i>",
        reply_markup=ReplyKeyboardRemove(),
    )


# =========================================================
# WORKPLACE
# =========================================================


@router.message(RegisterState.workplace)
async def process_workplace(message: Message, state: FSMContext):
    await state.update_data(workplace=message.text)
    data = await state.get_data()

    if is_editing(data):
        return await show_confirm(message, state)

    await state.set_state(RegisterState.phone_number)
    await message.answer(
        "<b>Telefon raqamingizni yuboring.</b>",
        reply_markup=contact_keyboard(),
    )


# =========================================================
# PHONE NUMBER
# =========================================================


@router.message(RegisterState.phone_number, F.contact)
async def process_phone_number(message: Message, state: FSMContext):
    contact: Contact = message.contact
    await state.update_data(phone_number=contact.phone_number)
    data = await state.get_data()

    if is_editing(data):
        return await show_confirm(message, state)

    await state.set_state(RegisterState.contest)
    await message.answer(
        "<b>Ishtirok etmoqchi bo‘lgan tanlovni tanlang.</b>",
        reply_markup=contest_keyboard(),
    )


# =========================================================
# CONTEST
# =========================================================


@router.message(RegisterState.contest, F.text == "⬅️ Bekor qilish")
async def back_to_phone_number(message: Message, state: FSMContext):
    await state.set_state(RegisterState.phone_number)
    await message.answer(
        "<b>Telefon raqamingizni yuboring.</b>",
        reply_markup=contact_keyboard(),
    )


@router.message(RegisterState.contest)
async def process_contest(message: Message, state: FSMContext):
    selected = CONTEST_MAPPING.get(message.text)

    if not selected:
        return await message.answer(
            "<i>Tanlovni tugmalar orqali tanlang.</i>",
            reply_markup=contest_keyboard(),
        )

    await state.update_data(contest=selected)
    await state.set_state(RegisterState.direction)
    await message.answer(
        "<b>Yo‘nalishni tanlang.</b>",
        reply_markup=direction_keyboard(),
    )


# =========================================================
# DIRECTION
# =========================================================


@router.message(RegisterState.direction, F.text == "⬅️ Bekor qilish")
async def back_to_contest(message: Message, state: FSMContext):
    await state.set_state(RegisterState.contest)
    await message.answer(
        "<b>Ishtirok etmoqchi bo‘lgan tanlovni tanlang.</b>",
        reply_markup=contest_keyboard(),
    )


@router.message(RegisterState.direction)
async def process_direction(message: Message, state: FSMContext):
    # "10-14 yosh toifasi (2012-2016)" dagi har qanday ko‘rinishni qabul qilish
    selected = DIRECTION_MAPPING.get(message.text)

    if not selected:
        return await message.answer(
            "<i>Yo‘nalishni tugmalar orqali tanlang.</i>",
            reply_markup=direction_keyboard(),
        )

    await state.update_data(direction=selected)
    await show_confirm(message, state)


# =========================================================
# CONFIRM — inline callback
# =========================================================


@router.callback_query(RegisterState.confirm, F.data == "confirm:yes")
async def confirm_registration(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    async with session_maker() as session:
        user_service = UserService(session)
        await user_service.complete_registration(
            user_id=callback.from_user.id,
            full_name=data["full_name"],
            birth_date=data["birth_date"],
            region=data["region"],
            district=data["district"],
            neighborhood=data["neighborhood"],
            workplace=data["workplace"],
            phone_number=data["phone_number"],
            contest=data["contest"],
            direction=data["direction"],
        )
        await session.commit()

    await state.clear()
    await callback.message.edit_text(
        "<b>Tabriklaymiz, siz muvaffaqiyatli ro‘yxatdan o‘tdingiz!</b>",
    )
    await callback.message.answer(
        "Asosiy menyu:",
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()


# =========================================================
# EDIT — har bir maydon uchun callback handler
# =========================================================


@router.callback_query(RegisterState.confirm, F.data.startswith("edit:"))
async def handle_edit(callback: CallbackQuery, state: FSMContext):
    field = callback.data.split(":")[1]
    data = await state.get_data()

    await callback.message.delete()

    if field == "full_name":
        await state.set_state(RegisterState.full_name)
        await callback.message.answer(
            "<b>Familiya, ism va sharifingizni kiriting.</b>\n"
            "<i>(Abdullayev Abdullajon Abdulla o‘g‘li)</i>",
            reply_markup=ReplyKeyboardRemove(),
        )

    elif field == "birth_date":
        await state.set_state(RegisterState.birth_date)
        await callback.message.answer(
            "<b>Tug‘ilgan sana va yilingizni kiriting.</b>\n"
            "<i>(Namuna: 31.01.2010)</i>",
            reply_markup=ReplyKeyboardRemove(),
        )

    elif field == "region":
        await state.set_state(RegisterState.region)
        await callback.message.answer(
            "<b>Hududingizni tanlang.</b>",
            reply_markup=regions_keyboard(),
        )

    elif field == "district":
        region_id = data.get("region_id")
        if region_id:
            await state.set_state(RegisterState.district)
            await callback.message.answer(
                "<b>Tuman/shaharni tanlang.</b>",
                reply_markup=districts_keyboard(region_id),
            )
        else:
            await state.set_state(RegisterState.region)
            await callback.message.answer(
                "<b>Avval hududni tanlang.</b>",
                reply_markup=regions_keyboard(),
            )

    elif field == "neighborhood":
        district_id = data.get("district_id")
        if district_id:
            await state.set_state(RegisterState.neighborhood)
            await callback.message.answer(
                "<b>Mahallani tanlang.</b>",
                reply_markup=mahallas_keyboard(district_id),
            )
        else:
            region_id = data.get("region_id")
            await state.set_state(RegisterState.district)
            await callback.message.answer(
                "<b>Avval tumanni tanlang.</b>",
                reply_markup=districts_keyboard(region_id)
                if region_id
                else regions_keyboard(),
            )

    elif field == "workplace":
        await state.set_state(RegisterState.workplace)
        await callback.message.answer(
            "<b>o‘qish yoki ish joyingizni kiriting.</b>\n"
            "<i>(Namuna: Talaba, o‘zMU 2-kurs)</i>",
            reply_markup=ReplyKeyboardRemove(),
        )

    elif field == "phone":
        await state.set_state(RegisterState.phone_number)
        await callback.message.answer(
            "<b>Telefon raqamingizni yuboring.</b>",
            reply_markup=contact_keyboard(),
        )

    elif field == "contest":
        await state.update_data(direction=None)
        await state.set_state(RegisterState.contest)
        await callback.message.answer(
            "<b>Ishtirok etmoqchi bo‘lgan tanlovni tanlang.</b>",
            reply_markup=contest_keyboard(),
        )

    await callback.answer()
