# Yaxshilanishlar ro'yxati — yoshkitobchibot

## 1. 🎯 Referal Ball Tizimi (Sozlanadigan)

**Fayl:** `database/services/settings_service.py` (yangi)

- Har bir taklif qilingan va ro'yxatdan o'tgan foydalanuvchi uchun beriladigan ball endi **admin panel orqali o'zgartiriladi**
- Default: **1 ball** har referal uchun
- O'zgartirish: Admin Panel → ⚙️ Sozlamalar → Referal ball
  - yoki: Admin Panel → 🔘 Tugmalar → 🎯 Referal ball sozlash
- `database/services/user_service.py` — `complete_registration()` endi `SettingsService`dan ball o'qiydi
- Targ'ibot sahifasida ham hozirgi ball ko'rsatiladi (+N ball)

---

## 2. 👤 Profil — Ma'lumotlarni O'zgartirish

**Fayl:** `app/handlers/users/menu.py` (mavjud)

- `profile_edit_keyboard()` tugmasi — `✏️ Ma'lumotlarni o'zgartirish`
- O'zgartirilishi mumkin: F.I.Sh., Ish/o'qish joyi, Mahalla
- Inline tugmalar orqali har bir maydon alohida tanlanadi

---

## 3. 📁 Handlers Tizimi Tartiblanishi

**Yangi struktura:**
```
app/handlers/
├── users/
│   ├── start.py
│   ├── menu.py         ← profil, reyting, targ'ibot
│   ├── test.py         ← test ishlash
│   ├── register.py
│   ├── help.py
│   └── prizes.py
└── admins/
    ├── main_admin.py
    ├── users.py
    ├── contest.py
    ├── settings_admin.py    ← YANGI: sozlamalar
    ├── tests/
    │   └── test_admin.py    ← YANGI: test boshqaruvi
    ├── buttons/
    │   └── button_admin.py  ← YANGI: tugmalar boshqaruvi
    ├── ads/
    └── channels/
```

---

## 4. 🧪 Test Bo'limi Yaxshilash

**Fayl:** `app/handlers/admins/tests/test_admin.py` (yangi)

Admin panel → 📋 Testlar ro'yxati orqali:
- ✅/🔴 Testni faollashtirish/o'chirish (toggle)
- 🗑 Test sessiyalarini tozalash (foydalanuvchilar qayta topshira olsin)
- 📊 Har bir test statistikasi (jami/tugatilgan sessiyalar)
- ⚙️ Test sozlamalari:
  - **Maksimal savollar soni** (default: 40 ta)
  - **Har savol uchun vaqt** (default: 90 soniya)
- Sozlamalar `BotSettings` jadvalida saqlanadi va `TestService` dinamik o'qiydi

---

## 5. 🏆 Konkurs Tizimi

**Fayl:** `app/handlers/admins/contest.py` (mavjud, yaxshilangan)

- ➕ Yangi konkurs yaratish (nom, tavsif, min referal, sovg'a)
- ▶️/⏹ Boshlash/to'xtatish
- 👥 Ishtirokchilar ro'yxati (shart bajarganlari)
- 🎲 Random g'olib tanlash
- ✏️ Referal balini qo'lda sozlash (foydalanuvchi ID bo'yicha)
- Targ'ibot bo'limi: aktiv konkurs bo'lsa — konkurs rejimida ko'rsatadi

---

## 6. 🔘 Tugmalar Tizimi

**Fayl:** `app/handlers/admins/buttons/button_admin.py` (yangi)

Admin Panel → 🔘 Tugmalar orqali:
- ➕ Yangi tugma yaratish:
  - **🔗 URL havola** — bosganda veb saytga o'tadi
  - **💬 Xabar matni** — bosganda foydalanuvchiga matn yuboriladi
- 📋 Barcha tugmalar ro'yxati
- 🟢/🔴 Yoqish/o'chirish
- 🗑 O'chirish
- 📢 **Ro'yxatdan o'tmaganlarga xabar yuborish** (broadcast)
- 🎯 Referal ball sozlash (qisqa yo'l)

---

## 7. ⚙️ Sozlamalar Panel

**Fayl:** `app/handlers/admins/settings_admin.py` (yangi)

Admin Panel → ⚙️ Sozlamalar:
- 🎯 Referal ball (har referal uchun N ball)
- 📝 Test maks. savollar soni
- ⏱ Test savol vaqti (soniya)
- 🗞 Targ'ibot bo'limi matni
- 👋 Ro'yxatdan o'tmagan uchun xabar
- 📋 Barchasini ko'rish (bir ekranda)

---

## 8. 📢 Broadcast Tizimi

**Fayl:** `app/handlers/admins/buttons/button_admin.py`

- Faqat **ro'yxatdan o'tmaganlar**ga xabar yuborish
- Progress ko'rsatiladi (har 20 ta da yangilanadi)
- Natija: muvaffaqiyatli/xato/jami statistika

---

## Migration

Yangi jadvallarni yaratish uchun:
```bash
python3 migrate.py
```

Yaratiladi:
- `bot_settings` — sozlamalar jadvali
- `custom_buttons` — tugmalar jadvali

---

## Admin Panel Yangi Ko'rinishi

```
📊 Statistika  |  📨 Xabar yuborish
🔐 Kanallar    |  📋 Testlar ro'yxati
👥 Foydalanuvchilar  |  🏆 Konkurs
🔘 Tugmalar    |  ⚙️ Sozlamalar
```
