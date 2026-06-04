# app/handlers/users/register.py

import re
from datetime import date, datetime
from aiogram.filters import Command

from aiogram import Bot, Router, F
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
# KONSTANTLAR
# =========================================================

CONTEST_LABELS = {
    ContestType.YOSH_KITOBXON_2026: '"Yosh kitobxon" tanlovi 2026',
}

DIRECTION_LABELS = {
    DirectionType.AGE_10_14: "10-14 yosh toifasi (2012-2016)",
    DirectionType.AGE_15_19: "15-19 yosh toifasi (2007-2011)",
    DirectionType.AGE_20_30: "20-30 yosh toifasi (1996-2006)",
}

CONTEST_MAPPING = {
    '"Yosh kitobxon" tanlovi 2026': ContestType.YOSH_KITOBXON_2026,
}

DIRECTION_MAPPING = {
    "10-14 yosh toifasi (2012-2016)": DirectionType.AGE_10_14,
    "15-19 yosh toifasi (2007-2011)": DirectionType.AGE_15_19,
    "20-30 yosh toifasi (1996-2006)": DirectionType.AGE_20_30,
}

# Yo‘nalishga mos tug‘ilgan yil oralig‘i
DIRECTION_BIRTH_YEARS = {
    DirectionType.AGE_10_14: (2012, 2016),
    DirectionType.AGE_15_19: (2007, 2011),
    DirectionType.AGE_20_30: (1996, 2006),
}

# Kirill alifbosi harflari (o‘zbek kirill)
CYRILLIC_PATTERN = re.compile(r"^[А-Яа-яЁёҒғҚқҲҳЎўҚқ\s'\-]+$")

# o‘zbek telefon raqami
PHONE_PATTERN = re.compile(r"^\+?998\s?(\d{2})\s?(\d{3})\s?(\d{2})\s?(\d{2})$")


# =========================================================
# VALIDATSIYA FUNKSIYALARI
# =========================================================


def validate_full_name(text: str) -> tuple[bool, str]:
    """
    F.I.Sh validatsiyasi:
    - Kamida 3 so‘z
    - Faqat kirill harflar
    - Oxirgi so‘z "o‘g‘li" yoki "qizi" bilan tugashi shart
    """
    if not text or not text.strip():
        return False, "❌ Ism bo‘sh bo‘lishi mumkin emas."

    words = text.strip().split()

    if len(words) < 3:
        return False, (
            "❌ <b>Kamida 3 so‘z kiriting.</b>\n\n"
            "📌 To‘g‘ri namuna:\n"
            "<i>Abdullayev Abdullajon Abdulla o‘g‘li</i>\n"
            "<i>Toshmatova Nilufar Bahodir qizi</i>"
        )

    last_word = words[-1].lower()
    if last_word not in ("o‘g‘li", "qizi", "o\u02bbg\u02bbli"):
        return False, (
            "❌ <b>Oxirgi so‘z <u>o‘g‘li</u> yoki <u>qizi</u> bo‘lishi shart.</b>\n\n"
            "📌 To‘g‘ri namuna:\n"
            "<i>Abdullayev Abdullajon Abdulla o‘g‘li</i>\n"
            "<i>Toshmatova Nilufar Bahodir qizi</i>"
        )

    # o‘g‘li / qizi dan oldingi so‘zlarni kirill tekshiruv
    check_words = words[:-1]
    for word in check_words:
        if not CYRILLIC_PATTERN.match(word):
            return False, (
                "❌ <b>Faqat kirill harflarida yozing.</b>\n\n"
                "📌 To‘g‘ri namuna:\n"
                "<i>Abdullayev Abdullajon Abdulla o‘g‘li</i>"
            )

    return True, ""


def validate_birth_date(text: str) -> tuple[bool, str, date | None]:
    """
    Tug‘ilgan sana validatsiyasi:
    - DD.MM.YYYY format
    - Kelajakdagi sana bo‘lmasligi
    - Yosh 10-35 oralig‘ida
    """
    try:
        birth_date = datetime.strptime(text.strip(), "%d.%m.%Y").date()
    except ValueError:
        return (
            False,
            (
                "❌ <b>Sana noto‘g‘ri formatda.</b>\n\n"
                "📌 Format: <code>KK.OO.YYYY</code>\n"
                "✅ Namuna: <code>15.03.2005</code>"
            ),
            None,
        )

    today = date.today()
    if birth_date >= today:
        return False, "❌ Tug‘ilgan sana kelajakda bo‘lishi mumkin emas.", None

    age = (today - birth_date).days // 365
    if age < 10 or age > 35:
        return (
            False,
            (
                "❌ <b>Yoshingiz 10 dan 35 gacha bo‘lishi kerak.</b>\n"
                f"Siz kiritgan sana bo‘yicha yoshingiz: <b>{age}</b>"
            ),
            None,
        )

    return True, "", birth_date


def validate_birth_date_by_direction(
    birth_date: date,
    direction: DirectionType,
) -> tuple[bool, str]:
    """
    Tug‘ilgan yilni tanlangan yo‘nalishga mosligini tekshirish.
    """
    min_year, max_year = DIRECTION_BIRTH_YEARS[direction]
    birth_year = birth_date.year

    if not (min_year <= birth_year <= max_year):
        direction_label = DIRECTION_LABELS[direction]
        return False, (
            f"❌ <b>Tug‘ilgan yilingiz ({birth_year}) tanlangan yo‘nalishga mos kelmaydi.</b>\n\n"
            f"📌 <b>{direction_label}</b> uchun tug‘ilgan yil: "
            f"<b>{min_year}–{max_year}</b> bo‘lishi kerak."
        )

    return True, ""


def validate_phone_manual(text: str) -> tuple[bool, str]:
    """
    Qo‘lda kiritilgan telefon raqam validatsiyasi.
    """
    cleaned = text.strip().replace(" ", "").replace("-", "")

    if not PHONE_PATTERN.match(cleaned):
        return False, (
            "❌ <b>Telefon raqam noto‘g‘ri formatda.</b>\n\n"
            "📌 Format: <code>+998 XX XXX XX XX</code>\n"
            "✅ Namuna: <code>+998 90 123 45 67</code>"
        )

    return True, ""


# =========================================================
# HELPERS
# =========================================================


def edit_fields_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="F.I.Sh", callback_data="edit:full_name"),
                InlineKeyboardButton(
                    text="Tug‘ilgan sana", callback_data="edit:birth_date"
                ),
            ],
            [
                InlineKeyboardButton(text="Hudud", callback_data="edit:region"),
                InlineKeyboardButton(text="Tuman", callback_data="edit:district"),
            ],
            [
                InlineKeyboardButton(text="Mahalla", callback_data="edit:neighborhood"),
                InlineKeyboardButton(
                    text="Ish/o‘qish joyi", callback_data="edit:workplace"
                ),
            ],
            [
                InlineKeyboardButton(text="Telefon", callback_data="edit:phone"),
                InlineKeyboardButton(
                    text="Tanlov/yo‘nalish", callback_data="edit:contest"
                ),
            ],
            [
                InlineKeyboardButton(text="Tasdiqlash", callback_data="confirm:yes"),
            ],
        ]
    )


async def show_confirm(message: Message, state: FSMContext):
    data = await state.get_data()

    contest_label = CONTEST_LABELS.get(
        data.get("contest"), str(data.get("contest", "—"))
    )
    direction_label = DIRECTION_LABELS.get(
        data.get("direction"), str(data.get("direction", "—"))
    )

    text = (
        "<b>Ma'lumotlaringizni tasdiqlang:</b>\n\n"
        f"<b>F.I.Sh:</b> {data.get('full_name', '—')}\n"
        f"<b>Tug‘ilgan sana:</b> {data.get('birth_date', '—')}\n"
        f"<b>Yashash joyi:</b> {data.get('region', '—')}, "
        f"{data.get('district', '—')}, {data.get('neighborhood', '—')}\n"
        f"<b>Ish/o‘qish:</b> {data.get('workplace', '—')}\n"
        f"<b>Telefon:</b> <code>{data.get('phone_number', '—')}</code>\n\n"
        f"<b>Tanlov:</b> {contest_label}\n"
        f"<b>Yo‘nalish:</b> {direction_label}\n\n"
        "<i>Tahrirlash uchun tegishli tugmani bosing.</i>"
    )

    await state.set_state(RegisterState.confirm)
    await message.answer(text, parse_mode="HTML", reply_markup=edit_fields_keyboard())


def is_editing(data: dict) -> bool:
    return bool(data.get("contest") and data.get("direction"))


def find_mahalla(district_id: int, text: str) -> dict | None:
    for m in mahallas_data:
        if int(m["district_id"]) != int(district_id):
            continue
        if m.get("mfy_name") == text or m["name"] == text:
            return m
    return None


# =========================================================
# START REGISTRATION
# =========================================================


@router.message(Command("register"))
@router.message(F.text == "📝 Ro‘yxatdan o‘tish")
async def start_registration(message: Message, state: FSMContext):
    await state.set_state(RegisterState.full_name)
    await message.answer(
        "<b>Familiya, ism va sharifingizni kiriting.</b>\n\n"
        "📌 <b>Qoidalar:</b>\n"
        "• Faqat kirill harflarida yozing\n"
        "• Kamida 3 so‘z bo‘lishi shart\n"
        "• Oxirida <b>o‘g‘li</b> yoki <b>qizi</b> deb yozing\n\n"
        "✅ <b>To‘g‘ri namuna:</b>\n"
        "<i>Abdullayev Abdullajon Abdulla o‘g‘li</i>\n"
        "<i>Toshmatova Nilufar Bahodir qizi</i>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )


# =========================================================
# FULL NAME
# =========================================================


@router.message(RegisterState.full_name)
async def process_full_name(message: Message, state: FSMContext):
    ok, err = validate_full_name(message.text or "")
    if not ok:
        return await message.answer(err, parse_mode="HTML")

    await state.update_data(full_name=message.text.strip())
    data = await state.get_data()

    if is_editing(data):
        return await show_confirm(message, state)

    await state.set_state(RegisterState.birth_date)
    await message.answer(
        "<b>Tug‘ilgan sana va yilingizni kiriting.</b>\n\n"
        "Format: <code>KK.OO.YYYY</code>\n"
        "Namuna: <code>15.03.2005</code>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )


# =========================================================
# BIRTH DATE
# =========================================================


@router.message(RegisterState.birth_date)
async def process_birth_date(message: Message, state: FSMContext):
    ok, err, birth_date = validate_birth_date(message.text or "")
    if not ok:
        return await message.answer(err, parse_mode="HTML")

    await state.update_data(birth_date=birth_date)
    data = await state.get_data()

    # Agar yo‘nalish allaqachon tanlangan bo‘lsa — mosligini tekshir
    if data.get("direction"):
        ok2, err2 = validate_birth_date_by_direction(birth_date, data["direction"])
        if not ok2:
            return await message.answer(
                err2
                + "\n\n📌 Yo‘nalishni o‘zgartirish uchun pastdagi tugmadan foydalaning.",
                parse_mode="HTML",
                reply_markup=edit_fields_keyboard(),
            )

    if is_editing(data):
        return await show_confirm(message, state)

    await state.set_state(RegisterState.region)
    await message.answer(
        "🗺 <b>Hududingizni tanlang.</b>",
        parse_mode="HTML",
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
            "❌ <i>Hududni tugmalar orqali tanlang.</i>",
            parse_mode="HTML",
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
        parse_mode="HTML",
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
        parse_mode="HTML",
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
            "❌ <i>Tumanni tugmalar orqali tanlang.</i>",
            parse_mode="HTML",
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
        parse_mode="HTML",
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
        parse_mode="HTML",
        reply_markup=districts_keyboard(region_id) if region_id else regions_keyboard(),
    )


@router.message(RegisterState.neighborhood)
async def process_neighborhood(message: Message, state: FSMContext):
    data = await state.get_data()
    district_id = data["district_id"]

    selected = find_mahalla(district_id, message.text)

    if not selected:
        await state.set_state(RegisterState.neighborhood_manual)
        return await message.answer(
            "<i>Mahalla ro‘yxatda topilmadi.</i>\n\n"
            "<b>Mahalla nomini o‘zingiz kiriting:</b>",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove(),
        )

    await state.update_data(neighborhood=selected["name"])
    data = await state.get_data()

    if is_editing(data):
        return await show_confirm(message, state)

    await state.set_state(RegisterState.workplace)
    await message.answer(
        "<b>o‘qish yoki ish joyingizni kiriting.</b>\n"
        "<i>Namuna: Talaba, o‘zMU 2-kurs</i>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )


# =========================================================
# NEIGHBORHOOD MANUAL
# =========================================================


@router.message(RegisterState.neighborhood_manual)
async def process_neighborhood_manual(message: Message, state: FSMContext):
    text = (message.text or "").strip()

    if len(text) < 3:
        return await message.answer(
            "❌ <i>Mahalla nomi juda qisqa. Kamida 3 ta harf kiriting.</i>",
            parse_mode="HTML",
        )

    await state.update_data(neighborhood=text)
    data = await state.get_data()

    if is_editing(data):
        return await show_confirm(message, state)

    await state.set_state(RegisterState.workplace)
    await message.answer(
        "<b>o‘qish yoki ish joyingizni kiriting.</b>\n"
        "<i>Namuna: Talaba, o‘zMU 2-kurs</i>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )


# =========================================================
# WORKPLACE
# =========================================================


@router.message(RegisterState.workplace)
async def process_workplace(message: Message, state: FSMContext):
    text = (message.text or "").strip()

    if len(text) < 3:
        return await message.answer(
            "❌ <i>Ish/o‘qish joyi juda qisqa. To‘liqroq kiriting.</i>",
            parse_mode="HTML",
        )

    await state.update_data(workplace=text)
    data = await state.get_data()

    if is_editing(data):
        return await show_confirm(message, state)

    await state.set_state(RegisterState.phone_number)
    await message.answer(
        "<b>Telefon raqamingizni yuboring.</b>\n\n"
        "Tugma orqali avtomatik yuborishingiz mumkin\n"
        "yoki qo‘lda kiriting: <code>+998901234567</code>",
        parse_mode="HTML",
        reply_markup=contact_keyboard(),
    )


# =========================================================
# PHONE NUMBER — kontakt orqali
# =========================================================


@router.message(RegisterState.phone_number, F.contact)
async def process_phone_contact(message: Message, state: FSMContext):
    contact: Contact = message.contact

    if contact.user_id and contact.user_id != message.from_user.id:
        return await message.answer(
            "❌ <b>Faqat o‘z telefon raqamingizni yuboring.</b>",
            parse_mode="HTML",
            reply_markup=contact_keyboard(),
        )

    await state.update_data(phone_number=contact.phone_number)
    data = await state.get_data()

    if is_editing(data):
        return await show_confirm(message, state)

    await state.set_state(RegisterState.contest)
    await message.answer(
        "<b>Ishtirok etmoqchi bo‘lgan tanlovni tanlang.</b>",
        parse_mode="HTML",
        reply_markup=contest_keyboard(),
    )


# Qo‘lda raqam kiritish
@router.message(RegisterState.phone_number, F.text)
async def process_phone_manual(message: Message, state: FSMContext):
    ok, err = validate_phone_manual(message.text or "")
    if not ok:
        return await message.answer(
            err, parse_mode="HTML", reply_markup=contact_keyboard()
        )

    cleaned = re.sub(r"[\s\-]", "", message.text.strip())
    if not cleaned.startswith("+"):
        cleaned = "+" + cleaned

    await state.update_data(phone_number=cleaned)
    data = await state.get_data()

    if is_editing(data):
        return await show_confirm(message, state)

    await state.set_state(RegisterState.contest)
    await message.answer(
        "<b>Ishtirok etmoqchi bo‘lgan tanlovni tanlang.</b>",
        parse_mode="HTML",
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
        parse_mode="HTML",
        reply_markup=contact_keyboard(),
    )


@router.message(RegisterState.contest)
async def process_contest(message: Message, state: FSMContext):
    selected = CONTEST_MAPPING.get(message.text)

    if not selected:
        return await message.answer(
            "<i>Tanlovni tugmalar orqali tanlang.</i>",
            parse_mode="HTML",
            reply_markup=contest_keyboard(),
        )

    await state.update_data(contest=selected)
    await state.set_state(RegisterState.direction)
    await message.answer(
        "<b>Yo‘nalishni tanlang.</b>",
        parse_mode="HTML",
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
        parse_mode="HTML",
        reply_markup=contest_keyboard(),
    )


@router.message(RegisterState.direction)
async def process_direction(message: Message, state: FSMContext):
    selected = DIRECTION_MAPPING.get(message.text)

    if not selected:
        return await message.answer(
            "❌ <i>Yo‘nalishni tugmalar orqali tanlang.</i>",
            parse_mode="HTML",
            reply_markup=direction_keyboard(),
        )

    data = await state.get_data()

    # Tug‘ilgan sana yo‘nalishga mos kelishini tekshirish
    birth_date = data.get("birth_date")
    if birth_date:
        ok, err = validate_birth_date_by_direction(birth_date, selected)
        if not ok:
            return await message.answer(
                err
                + "\n\n📌 <b>Boshqa yo‘nalish tanlang yoki tug‘ilgan sanangizni o‘zgartiring.</b>",
                parse_mode="HTML",
                reply_markup=direction_keyboard(),
            )

    await state.update_data(direction=selected)
    await show_confirm(message, state)


# =========================================================
# CONFIRM — inline callback
# =========================================================


@router.callback_query(RegisterState.confirm, F.data == "confirm:yes")
async def confirm_registration(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
):
    data = await state.get_data()

    # Yakuniy tekshiruv
    birth_date = data.get("birth_date")
    direction = data.get("direction")
    if birth_date and direction:
        ok, err = validate_birth_date_by_direction(birth_date, direction)
        if not ok:
            await callback.answer("Yo‘nalish va yoshingiz mos emas!", show_alert=True)
            return

    async with session_maker() as session:
        user_service = UserService(session)

        await user_service.complete_registration(
            user_id=callback.from_user.id,
            bot=bot,
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

    await state.clear()

    await callback.message.edit_text(
        "✅ <b>Tabriklaymiz, siz muvaffaqiyatli ro‘yxatdan o‘tdingiz!</b>",
        parse_mode="HTML",
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
            "👤 <b>Familiya, ism va sharifingizni kiriting.</b>\n\n"
            "📌 <b>Qoidalar:</b>\n"
            "• Faqat kirill harflarida yozing\n"
            "• Kamida 3 so‘z bo‘lishi shart\n"
            "• Oxirida <b>o‘g‘li</b> yoki <b>qizi</b> deb yozing\n\n"
            "✅ Namuna: <i>Abdullayev Abdullajon Abdulla o‘g‘li</i>",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove(),
        )

    elif field == "birth_date":
        await state.set_state(RegisterState.birth_date)
        await callback.message.answer(
            "📅 <b>Tug‘ilgan sana va yilingizni kiriting.</b>\n\n"
            "📌 Format: <code>KK.OO.YYYY</code>\n"
            "✅ Namuna: <code>15.03.2005</code>",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove(),
        )

    elif field == "region":
        await state.set_state(RegisterState.region)
        await callback.message.answer(
            "🗺 <b>Hududingizni tanlang.</b>",
            parse_mode="HTML",
            reply_markup=regions_keyboard(),
        )

    elif field == "district":
        region_id = data.get("region_id")
        if region_id:
            await state.set_state(RegisterState.district)
            await callback.message.answer(
                "🏙 <b>Tuman/shaharni tanlang.</b>",
                parse_mode="HTML",
                reply_markup=districts_keyboard(region_id),
            )
        else:
            await state.set_state(RegisterState.region)
            await callback.message.answer(
                "🗺 <b>Avval hududni tanlang.</b>",
                parse_mode="HTML",
                reply_markup=regions_keyboard(),
            )

    elif field == "neighborhood":
        district_id = data.get("district_id")
        if district_id:
            await state.set_state(RegisterState.neighborhood)
            await callback.message.answer(
                "🏘 <b>Mahallani tanlang.</b>",
                parse_mode="HTML",
                reply_markup=mahallas_keyboard(district_id),
            )
        else:
            region_id = data.get("region_id")
            await state.set_state(RegisterState.district)
            await callback.message.answer(
                "🏙 <b>Avval tumanni tanlang.</b>",
                parse_mode="HTML",
                reply_markup=districts_keyboard(region_id)
                if region_id
                else regions_keyboard(),
            )

    elif field == "workplace":
        await state.set_state(RegisterState.workplace)
        await callback.message.answer(
            "🏫 <b>o‘qish yoki ish joyingizni kiriting.</b>\n"
            "<i>Namuna: Talaba, o‘zMU 2-kurs</i>",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove(),
        )

    elif field == "phone":
        await state.set_state(RegisterState.phone_number)
        await callback.message.answer(
            "📞 <b>Telefon raqamingizni yuboring.</b>",
            parse_mode="HTML",
            reply_markup=contact_keyboard(),
        )

    elif field == "contest":
        await state.update_data(direction=None)
        await state.set_state(RegisterState.contest)
        await callback.message.answer(
            "🏆 <b>Ishtirok etmoqchi bo‘lgan tanlovni tanlang.</b>",
            parse_mode="HTML",
            reply_markup=contest_keyboard(),
        )

    await callback.answer()
