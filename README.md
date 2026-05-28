# 📚 Yosh Kitobxon Bot

**Yosh Kitobxon Bot** — o‘zbekistondagi "Yosh Kitobxon 2026" tanloviga onlayn ro‘yxatdan o‘tishni avtomatlashtiruvchi Telegram bot. Bot foydalanuvchini qadam-baqadam ro‘yxatdan o‘tkazadi, obunani tekshiradi, referal tizimi orqali ball yig‘ish imkonini beradi va admin paneli orqali to‘liq boshqariladi.

---

## 📁 Loyiha tuzilmasi

```
yoshkitobchibot/
│
├── main.py                        # Botni ishga tushiradigan asosiy fayl
├── api.py                         # o‘zbekiston hududlari ma'lumotini yuklash skripti
├── requirements.txt               # Kutubxonalar ro‘yxati (pip freeze)
├── .env                           # Muhit o‘zgaruvchilari (token, adminlar, IP)
│
├── data/
│   ├── config.py                  # .env dan BOT_TOKEN, ADMINS, IP ni o‘qish
│   └── checking.py                # Foydalanuvchini kanalda a'zo ekanligini tekshirish
│
├── database/
│   ├── database.py                # SQLAlchemy engine va sessiya sozlamalari
│   ├── models.py                  # User, Channel, ChannelJoin, Ad modellari
│   └── services/
│       ├── user_service.py        # Foydalanuvchi CRUD va ballar
│       ├── channel_service.py     # Kanal CRUD
│       └── join_request_service.py# Join request kuzatuvi
│
├── middlewares/
│   ├── checking_middlewares.py    # Obuna tekshirish middleware (SubscriptionMiddleware)
│   ├── throttling.py              # So‘rovlar chastotasini cheklash
│   └── __init__.py                # Middlewareni dispatcherga ulash
│
├── app/
│   ├── data/
│   │   ├── regions.json           # o‘zbekiston viloyatlari
│   │   ├── districts.json         # Tumanlar
│   │   └── villages.json          # MFY lar (mahallalar)
│   │
│   ├── filters/
│   │   └── is_admin.py            # Admin filteri
│   │
│   ├── handlers/
│   │   ├── users/
│   │   │   ├── start.py           # /start komandasi va referal tizimi
│   │   │   ├── register.py        # Ro‘yxatdan o‘tish oqimi (FSM)
│   │   │   ├── menu.py            # Asosiy menyu
│   │   │   └── help.py            # Yordam
│   │   ├── admins/
│   │   │   ├── main_admin.py      # /panel komandasi, reklama, xabar yuborish
│   │   │   └── channels/
│   │   │       ├── add_channel.py     # Kanal qo‘shish
│   │   │       ├── delete_channel.py  # Kanalni o‘chirish
│   │   │       └── view_channels.py   # Kanallar ro‘yxati
│   │   └── channels/
│   │       └── chatjoin.py        # ChatJoinRequest hodisasini qayta ishlash
│   │
│   ├── keyboards/
│   │   ├── reply.py               # Reply klaviaturalar (viloyat, tuman, mahalla...)
│   │   └── inline.py              # Inline klaviaturalar
│   │
│   ├── states/
│   │   ├── register.py            # Ro‘yxatdan o‘tish holatlari (FSMState)
│   │   └── add_channel.py         # Kanal qo‘shish holatlari
│   │
│   └── utils/
│       ├── constants.py           # Umumiy konstantalar
│       ├── strings.py             # Bot xabarlari (matnlar)
│       ├── db_filler.py           # Ma'lumotlar bazasini boshlang‘ich to‘ldirish
│       ├── notify_admins.py       # Adminlarga bildirishnoma yuborish
│       ├── set_bot_commands.py    # Bot komandalarini o‘rnatish
│       └── misc/
│           ├── logging.py         # Logger sozlamalari
│           └── throttling.py      # Throttling yordamchi funksiyalar
│
└── scripts/
    └── add_user.py                # Foydalanuvchini qo‘lda qo‘shish skripti
```

---

## ⚙️ Texnologiyalar

| Texnologiya | Versiya | Maqsad |
|---|---|---|
| Python | 3.12 | Asosiy til |
| Aiogram | 3.21.0 | Telegram Bot Framework |
| SQLAlchemy | 2.0.50 | Async ORM |
| aiosqlite | 0.22.0 | SQLite async driver |
| environs | 15.0.1 | .env faylini o‘qish |
| requests | 2.34.2 | Hudud API so‘rovlari |

---

## 🗄️ Ma'lumotlar bazasi modellari

### `User` — Foydalanuvchi
| Maydon | Turi | Tavsif |
|---|---|---|
| `user_id` | BigInteger | Telegram ID (unique) |
| `full_name` | String | F.I.Sh |
| `birth_date` | Date | Tug‘ilgan sana |
| `phone_number` | String | Telefon raqami (unique) |
| `region` | String | Viloyat |
| `district` | String | Tuman |
| `neighborhood` | String | Mahalla |
| `workplace` | String | Ish/o‘qish joyi |
| `contest` | Enum | Tanlov (`yosh_kitobxon_2026`) |
| `direction` | Enum | Yosh toifasi (10-14, 15-19, 20-30) |
| `referral_score` | Integer | Referal ballari |
| `test_score` | Integer | Test ballari |
| `total_score` | Integer | Umumiy ball |
| `referred_by` | BigInteger | Kim taklif qildi (FK → users) |
| `is_admin` | Boolean | Admin yoki yo‘q |
| `is_registered` | Boolean | Ro‘yxatdan o‘tgan yoki yo‘q |

### `Channel` — Majburiy obuna kanali
Admin tomonidan qo‘shilgan kanallar. `is_private` uchun join request orqali tekshiriladi, ochiq kanallarda `get_chat_member` ishlatiladi.

### `ChannelJoin` — Obuna tarixi
Qaysi foydalanuvchi qaysi kanalga qachon qo‘shilgani va tark etgani qayd etiladi.

### `Ad` — Reklama
Admin tomonidan boshqariladigan reklama bloklari (sarlavha, matn, tugmalar).

---

## 🔄 Ro‘yxatdan o‘tish oqimi

Bot FSM (Finite State Machine) yordamida foydalanuvchini quyidagi ketma-ket bosqichlardan o‘tkazadi:

```
/start
  └─ Yangi foydalanuvchi → [Ro‘yxatdan o‘tish tugmasi]
       ↓
  F.I.Sh kiritish
       ↓
  Tug‘ilgan sana (DD.MM.YYYY)
       ↓
  Viloyat tanlash (reply keyboard)
       ↓
  Tuman tanlash
       ↓
  Mahalla tanlash (yoki qo‘lda kiritish)
       ↓
  Ish/o‘qish joyi
       ↓
  Telefon raqami (Contact orqali)
       ↓
  Tanlov tanlash ("Yosh kitobxon" 2026)
       ↓
  Yosh toifasi tanlash (10-14 / 15-19 / 20-30)
       ↓
  Ma'lumotlarni tasdiqlash (inline tugmalar)
       ↓
  ✅ Ro‘yxatdan o‘tish yakunlandi → Asosiy menyu
```

Tasdiqlash sahifasida har bir maydonni alohida o‘zgartirish mumkin — foydalanuvchi tegishli inline tugmani bosib, faqat kerakli qadamga qaytadi.

---

## 🛡️ Obuna tekshirish (SubscriptionMiddleware)

Bot har bir xabar va callback qo‘yida barcha faol kanallarni tekshiradi:

- **Ochiq kanallar** — `get_chat_member` orqali a'zolik aniqlanadi
- **Yopiq kanallar** — `ChannelJoin` jadvalidagi faol yozuv tekshiriladi
- Obuna bo‘lmagan kanallar uchun "Obuna bo‘lish" tugmasi ko‘rsatiladi
- Adminlar ushbu tekshiruvdan o‘tkazilmaydi

---

## 🔑 Referal tizimi

Har bir foydalanuvchining shaxsiy havolasi `https://t.me/<bot>?start=<user_id>` ko‘rinishida bo‘ladi. Yangi foydalanuvchi bu havola orqali kelganda `referred_by` maydoni saqlanadi va referal ball yig‘ila boshlaydi.

---

## 🔐 Admin panel

`/panel` komandasi orqali adminlar quyidagi imkoniyatlardan foydalanadi:

- **📢 Reklama** — reklama blokini boshqarish
- **📨 Xabar yuborish** — barcha foydalanuvchilarga broadcast
- **📡 Kanallar** — majburiy obuna kanallarini qo‘shish, ko‘rish, o‘chirish

---

## 🚀 Ishga tushirish

### 1. Repozitoriyani klonlash

```bash
git clone <repo_url>
cd yoshkitobchibot
```

### 2. Virtual muhit yaratish

```bash
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
.venv\Scripts\activate           # Windows
```

### 3. Kutubxonalarni o‘rnatish

```bash
pip install -r requirements.txt
```

### 4. `.env` faylini sozlash

```env
BOT_TOKEN=1234567890:AABBccDDeeFFggHHiiJJ
ADMINS=123456789,987654321
ip=0.0.0.0
```

| o‘zgaruvchi | Tavsif |
|---|---|
| `BOT_TOKEN` | BotFather dan olingan token |
| `ADMINS` | Admin Telegram ID lari (vergul bilan) |
| `ip` | Server IP manzili (agar kerak bo‘lsa) |

### 5. Hudud ma'lumotlarini yangilash (ixtiyoriy)

`app/data/` papkasidagi `regions.json`, `districts.json`, `villages.json` fayllari allaqachon to‘ldirilgan. Agar yangilash kerak bo‘lsa:

```bash
python api.py
cp -r data_hududlar/regions.json   app/data/
cp -r data_hududlar/districts.json app/data/
cp -r data_hududlar/mfy.json       app/data/villages.json
```

### 6. Botni ishga tushirish

```bash
python main.py
```

---

## 📦 Asosiy kutubxonalar

```
aiogram==3.21.0
SQLAlchemy==2.0.50
aiosqlite==0.22.0
environs==15.0.1
requests==2.34.2
pydantic==2.11.10
```

---

## 📄 Litsenziya

Ushbu loyiha ochiq manbali. Istalgan maqsad uchun erkin foydalanishingiz mumkin.