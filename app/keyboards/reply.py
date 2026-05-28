# app/keyboards/reply/register.py

import json
from functools import lru_cache
from pathlib import Path

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder

# =========================================================
# JSON FAYLLARI Yo‘LI
# =========================================================

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# =========================================================
# MA'LUMOTLARNI YUKLASH (bir marta, cache'lanadi)
# =========================================================


@lru_cache(maxsize=1)
def _load_regions() -> list[dict]:
    with open(DATA_DIR / "regions.json", encoding="utf-8-sig") as f:
        return sorted(json.load(f), key=lambda x: x["name"])


@lru_cache(maxsize=1)
def _load_districts() -> list[dict]:
    with open(DATA_DIR / "districts.json", encoding="utf-8-sig") as f:
        return sorted(json.load(f), key=lambda x: x["name"])


@lru_cache(maxsize=1)
def _load_villages() -> list[dict]:
    with open(DATA_DIR / "villages.json", encoding="utf-8-sig") as f:
        return sorted(json.load(f), key=lambda x: x["name"])


# =========================================================
# HANDLER DA ISHLATILADIGAN Ro‘YXATLAR
# — regions_data, districts_data, mahallas_data
# — handler import qilib to‘g‘ridan-to‘g‘ri ishlatadi
# =========================================================

regions_data: list[dict] = _load_regions()
districts_data: list[dict] = _load_districts()
mahallas_data: list[dict] = _load_villages()  # handler: mahallas_data
villages_data: list[dict] = mahallas_data  # alias


# =========================================================
# START KEYBOARD
# =========================================================


def start_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="📝 Ro‘yxatdan o‘tish"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


# =========================================================
# CONTACT KEYBOARD
# =========================================================


def contact_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(
        KeyboardButton(
            text="📞 Telefon raqam yuborish",
            request_contact=True,
        )
    )
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


# =========================================================
# VILOYATLAR KEYBOARD
# — tartiblangan, har biri alohida qatorda
# =========================================================


def regions_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    for region in regions_data:
        builder.add(KeyboardButton(text=region["name"]))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


# =========================================================
# TUMANLAR KEYBOARD
# — berilgan region_id ga tegishli tumanlar
# =========================================================


def districts_keyboard(region_id: int) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    filtered = [d for d in districts_data if int(d["region_id"]) == int(region_id)]
    for district in filtered:
        builder.add(KeyboardButton(text=district["name"]))
    builder.add(KeyboardButton(text="⬅️ Orqaga"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


# =========================================================
# MAHALLA / MFY KEYBOARD
# — berilgan district_id ga tegishli mahallalar
# — mfy_name bo‘lsa shu, bo‘lmasa name ko‘rsatiladi
# =========================================================


def villages_keyboard(district_id: int) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    filtered = [v for v in mahallas_data if int(v["district_id"]) == int(district_id)]
    for village in filtered:
        label = village.get("mfy_name") or village["name"]
        builder.add(KeyboardButton(text=label))
    builder.add(KeyboardButton(text="⬅️ Orqaga"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


# =========================================================
# BACKWARD COMPATIBILITY
# — handler: mahallas_keyboard(district_id)
# =========================================================

mahallas_keyboard = villages_keyboard


# =========================================================
# TANLOV KEYBOARD
# =========================================================


def contest_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="\u201cYosh kitobxon\u201d tanlovi 2026"))
    builder.add(KeyboardButton(text="⬅️ Bekor qilish"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


# =========================================================
# Yo‘NALISH KEYBOARD
# =========================================================


def direction_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="10-14 yosh toifasi (2012-2016)"))
    builder.add(KeyboardButton(text="15-19 yosh toifasi (2007-2011)"))
    builder.add(KeyboardButton(text="20-30 yosh toifasi (1996-2006)"))
    builder.add(KeyboardButton(text="⬅️ Bekor qilish"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


# =========================================================
# TASDIQLASH KEYBOARD
# =========================================================


def confirm_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="✅ Tasdiqlash"))
    builder.add(KeyboardButton(text="✏️ Qayta to‘ldirish"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


# =========================================================
# ASOSIY MENYU KEYBOARD
# =========================================================


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="📄 Test"))
    builder.add(KeyboardButton(text="📊 Reyting"))
    builder.add(KeyboardButton(text="👤 Profil"))
    builder.add(KeyboardButton(text="🗞 Targ‘ibot"))
    builder.add(KeyboardButton(text="🎁 Sovg‘alar"))
    builder.add(KeyboardButton(text="❓ Yordam"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📊 Statistika"),
                KeyboardButton(text="📨 Xabar yuborish"),
            ],
            [
                KeyboardButton(text="🔐 Kanallar"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Admin panel",
    )
