# 🤖 Aiogram 3 Template

`Aiogram 3 Template` — bu Telegram bot yaratishni soddalashtiradigan, modulli va kengaytiriladigan shablon loyiha. Ushbu template Aiogram 3 asosida yozilgan bo‘lib, zamonaviy Python texnikalariga asoslangan.

## 📁 Loyiha tuzilmasi

aiogram 3 template/

├── app/ # Botning handler va routerlari

├── data/ # Konfiguratsiyalar va statik ma'lumotlar

├── database/ # Ma'lumotlar bazasi bilan ishlash

├── middlewares/ # Aiogram middleware'lari

├── main.py # Bot ishga tushadigan fayl

├── .env # Muhit o‘zgaruvchilari (TOKEN, DB_URL va h.k.)

├── .venv/ # Virtual muhit (version control'ga qo‘shilmasin)

└── requirements.txt # Kutubxonalar ro‘yxati


## 🚀 Ishga tushirish

1. **Virtual muhit yaratish va faollashtirish:**
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```
2. **Kerakli kutubxonalarni o‘rnatish:**
```bash
pip install -r requirements.txt
.env faylini to‘ldirish:
```
3. **.env faylini to‘ldirish:**
```bash
ADMINS=1234567890
BOT_TOKEN=1234567890:qwertyuiopasdfghjkl;
```
4. **Botni ishga tushurish:**
```bash
python main.py
```

**⚙ Xususiyatlar**

✅ Toza va modulli tuzilma

✅ Aiogram 3'ga to‘liq moslashtirilgan

✅ Middleware'lar bilan kengaytirilgan arxitektura

✅ .env bilan qulay sozlash imkoniyati

✅ Oson tushunarli va kengaytiriladigan kod bazasi

**📄 Litsenziya**

Ushbu template ochiq manbali. Istalgan maqsad uchun erkin foydalanishingiz mumkin.
