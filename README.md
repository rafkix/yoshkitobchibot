# 🤖 yoshkitobchibot — Tizim Yangilanishlari & Arxitektura

<p align="center">
  <img src="https://img.shields.io/badge/Version-2.0.0-blue?style=for-the-badge&logo=github" alt="Version">
  <img src="https://img.shields.io/badge/Framework-aiogram_v3.x-green?style=for-the-badge&logo=telegram" alt="Framework">
  <img src="https://img.shields.io/badge/Database-SQLAlchemy%20%7C%20PostgreSQL-orange?style=for-the-badge" alt="Database">
</p>

---

## 🚀 Tizimdagi Yangi Funksiyalar

### 1. 🎯 Dinamik Referal Ball Tizimi
* **Fayl:** `database/services/settings_service.py` 🆕
* **Imkoniyat:** Taklif qilingan va muvaffaqiyatli ro‘yxatdan o‘tgan foydalanuvchi uchun beriladigan ball endi to‘liq **dinamik** ko‘rinishga keltirildi.
* **Boshqaruv:** `Admin Panel ➡️ ⚙️ Sozlamalar ➡️ Referal ball` yoki tezkor yo‘lak orqali sozlanadi.
* **Logika:** `user_service.py` ichidagi `complete_registration()` funksiyasi endi statik qiymat emas, balki `SettingsService` orqali bazadagi joriy ballni o‘qiydi.
* **Foydalanuvchi interfeysi:** Targ‘ibot sahifasida joriy ball qiymati (`+N ball`) real vaqtda yangilanib turadi.

### 2. 👤 Profil ma'lumotlarini tahrirlash
* **Fayl:** `app/handlers/users/menu.py` 🔄
* **Imkoniyat:** Profil menyusiga interaktiv `✏️ Ma'lumotlarni o‘zgartirish` inline-tugmasi qo‘shildi.
* Foydalanuvchilar quyidagi ma'lumotlarni to‘liq qayta tahrirlashlari mumkin:
  * 📝 **F.I.Sh.** (To‘liq ism-sharif)
  * 🏢 **Ish/o‘qish joyi** (Muassasa nomi)
  * 📍 **Mahalla** (Yashash hududi)

### 3. 🧪 Kengaytirilgan Test Boshqaruvi
* **Fayl:** `app/handlers/admins/tests/test_admin.py` 🆕
* **Admin panel orqali to‘liq nazorat:**
  * `✅ / 🔴` **Status Toggle:** Testlarni bir marta bosish bilan yoqish yoki o‘chirish.
  * `🗑 Sessiyalarni tozalash:` Foydalanuvchilar testni qaytadan topshira olishlari uchun eski urinishlarni o‘chirish.
  * `📊 Statistika:` Har bir test bo‘yicha jami boshlangan va muvaffaqiyatli tugatilgan sessiyalar hisoboti.
  * `⚙️ Dinamik Limitlar:` Maksimal savollar soni (*Default: 40 ta*) va har bir savol uchun vaqt taymeri (*Default: 90 soniya*) `BotSettings` jadvali orqali dinamik boshqariladi.

### 4. 🏆 Konkurs (Musobaqa) Moduli
* **Fayl:** `app/handlers/admins/contest.py` 🔄
* **Yaratish va Boshqaruv:** Yangi konkurs yaratish (nomi, tavsifi, minimal referal limiti, sovg‘alar) hamda start (`▶️`) / stop (`⏹`) tugmalari.
* **g‘oliblar:** Shartlarni bajargan ishtirokchilar ro‘yxatidan adolatli `🎲 Random` (tasodifiy) g‘olib aniqlash algoritmi.
* **Korreksiya:** Foydalanuvchining referal ballarini ID bo‘yicha admin panelidan qo‘lda sozlash imkoniyati.
* **Avtomatlashtirish:** Aktiv konkurs bo‘lganda, foydalanuvchining **Targ‘ibot** bo‘limi avtomatik ravishda **Konkurs Rejimi**ga o‘tadi.

### 5. 🔘 Dinamik Tugmalar Tizimi
* **Fayl:** `app/handlers/admins/buttons/button_admin.py` 🆕
* **Imkoniyat:** Bot ichida admin tomonidan istalgan vaqtda yangi tugmalar yaratish:
  * `🔗 URL Havola` — Tashqi veb-saytlarga yo‘naltiruvchi tugma.
  * `💬 Xabar matni` — Bosilganda foydalanuvchiga bot nomidan maxsus matn qaytaruvchi tugma.
* Tugmalarni yoqish/o‘chirish (`🟢/🔴`) va to‘liq o‘chirish (`🗑`) paneli.

### 6. 📢 Maqsadli Broadcast (Target-Xabar)
* **Fayl:** `app/handlers/admins/buttons/button_admin.py`
* **Target:** Botga start bosgan, biroq hali **ro‘yxatdan o‘tmagan** foydalanuvchilarga yo‘naltirilgan xabarnomalar.
* **Progress Tracking:** Har 20 ta yuborilgan xabarda admin ekrani real vaqtda yangilanadi.
* **Natija:** Muvaffaqiyatli yetkazilganlar, xatoliklar va jami statistika yakunda taqdim etiladi.

---

## 📁 Loyiha Strukturasi (Handlers)

Kod bazasi modullilik tamoyili asosida quyidagicha tartiblandi:

```text
app/handlers/
├── 👤 users/
│   ├── start.py          # Botni ishga tushirish va referal triggerlari
│   ├── register.py       # Bosqichma-bosqich ro‘yxatdan o‘tish logikasi
│   ├── menu.py           # Profil, reyting va targ‘ibot menyulari
│   ├── test.py           # Test topshirish va taymer logikasi
│   ├── help.py           # Yo‘riqnoma va ko‘mak
│   └── prizes.py         # Sovrinlar ro‘yxati
│
└── 👑 admins/
    ├── main_admin.py     # Asosiy boshqaruv paneli
    ├── users.py          # Foydalanuvchilar bazasi va qidiruv
    ├── contest.py        # Konkurs va Randomizer moduli
    ├── settings_admin.py # Tizim va konfiguratsiya sozlamalari 🆕
    ├── ads/              # Reklama menejmenti
    ├── channels/         # Majburiy obunalar nazorati
    ├── tests/
    │   └── test_admin.py # Test sozlamalari va statistikasi 🆕
    └── buttons/
        └── button_admin.py # Dinamik tugmalar va target-broadcast 🆕
