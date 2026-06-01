# 🤖 yoshkitobchibot — Yangilanishlar va Tizim Arxitekturasi

Ushbu hujjat **yoshkitobchibot** loyihasining yangi funksionalligi, ma'lumotlar strukturasi va handlerlar arxitekturasini o'z ichiga oladi. Yangilanishlar tizimni yanada dinamik, adminlar uchun moslashuvchan va foydalanuvchilar uchun qulay qilishga qaratilgan.

---

## 🚀 Asosiy Yaxshilanishlar Tizimi

### 1. 🎯 Dinamik Referal Ball Tizimi
* **Fayl:** `database/services/settings_service.py` *(Yangi)*
* Har bir taklif qilingan va muvaffaqiyatli ro'yxatdan o'tgan foydalanuvchi uchun beriladigan ball endi to'liq admin panel orqali boshqariladi.
* **Standart qiymat (Default):** `1 ball`
* **Boshqaruv interfeysi:** `Admin Panel → ⚙️ Sozlamalar → Referal ball` yoki `Admin Panel → 🔘 Tugmalar → 🎯 Referal ball sozlash` orqali tezkor kirish.
* `database/services/user_service.py` ichidagi `complete_registration()` funksiyasi ball miqdorini dinamik ravishda `SettingsService`dan o'qiydi.
* Foydalanuvchining **Targ'ibot** sahifasida joriy ball qiymati (`+N ball`) real vaqtda ko'rsatiladi.

### 2. 👤 Profil ma'lumotlarini tahrirlash
* **Fayl:** `app/handlers/users/menu.py` *(Mavjud)*
* Profil bo'limiga yangi `✏️ Ma'lumotlarni o'zgartirish` inline tugmasi qo'shildi (`profile_edit_keyboard()`).
* Foydalanuvchilar quyidagi ma'lumotlarini alohida interaktiv tugmalar orqali tahrirlashlari mumkin:
  * 📝 F.I.Sh. (To'liq ism-sharif)
  * 🏢 Ish yoki o'qish joyi
  * 📍 Mahalla / Istiqomat joyi

### 3. 🧪 Kengaytirilgan Test Boshqaruvi
* **Fayl:** `app/handlers/admins/tests/test_admin.py` *(Yangi)*
* Adminlar uchun `📋 Testlar ro'yxati` menyusi orqali quyidagi imkoniyatlar yaratildi:
  * 🔄 **Status Toggle:** Testlarni bir marta bosish bilan faollashtirish yoki vaqtincha o'chirish (`✅/🔴`).
  * 🗑 **Sessiyalarni tozalash:** Muayan test bo'yicha foydalanuvchilarning urinishlarini tozalash (qayta topshirish imkonini berish).
  * 📊 **Statistika:** Har bir test bo'yicha jami boshlangan va yakunlangan sessiyalar hisoboti.
  * ⚙️ **Dinamik konfiguratsiya:**
    * *Maksimal savollar soni* (Default: `40 ta`)
    * *Har bir savol uchun ajratilgan vaqt* (Default: `90 soniya`)
  * Sozlamalar `BotSettings` jadvalida saqlanadi va `TestService` orqali dinamik hisoblanadi.

### 4. 🏆 Konkurs (Musobaqa) Tizimi
* **Fayl:** `app/handlers/admins/contest.py` *(Yaxshilangan)*
* **Konkurs menejmenti:** Yangi konkurs yaratish (nomi, tavsifi, minimal referal limiti, sovg'alar).
* **Nazorat:** Konkursni boshlash (`▶️`) va to'xtatish (`⏹`) tugmalari.
* **G'oliblarni aniqlash:** Shartlarni bajargan ishtirokchilar ro'yxatidan tasodifiy (`🎲 Random`) g'olibni tanlash algoritmi.
* **Balans nazorati:** Foydalanuvchining referal ballarini ID bo'yicha qo'lda korreksiya qilish (tahrirlash) imkoniyati.
* Foydalanuvchi interfeysidagi **Targ'ibot bo'limi** faol konkurs mavjud bo'lganda avtomatik ravishda "Konkurs Rejimi"ga moslashadi.

### 5. 🔘 Dinamik Tugmalar Boshqaruvi
* **Fayl:** `app/handlers/admins/buttons/button_admin.py` *(Yangi)*
* Admin panel orqali ixtiyoriy keyboard tugmalarini yaratish va boshqarish:
  * **🔗 URL Havola:** Bosilganda tashqi veb-resursga yo'naltiruvchi tugma.
  * **💬 Xabar Matni:** Bosilganda foydalanuvchiga bot nomidan oldindan tayyorlangan matnni qaytaruvchi tugma.
* Tugmalarni yoqish/o'chirish (`🟢/🔴`) va to'liq o'chirish (`🗑`) funksiyalari.
* Dinamik tugmalar menyusidan referal ballarini tezkor sozlash (`🎯`) oynasiga o'tish linki.

### 6. ⚙️ Markazlashtirilgan Sozlamalar Paneli
* **Fayl:** `app/handlers/admins/settings_admin.py` *(Yangi)*
* Tizim parametrlarini bir joydan turib boshqarish paneli:
  * 🎯 Har bir taklif uchun referal ball miqdori
  * 📝 Testning maksimal savollar soni
  * ⏱ Har bir savol taymeri (soniyalarda)
  * 🗞 Targ'ibot bo'limi uchun maxsus kontent/matn
  * 👋 Ro'yxatdan o'tmagan foydalanuvchilar uchun start xabari
  * 📋 Barcha joriy sozlamalarni yagona ekranda qulay ko'rish (Dashboard)

### 7. 📢 Maqsadli Broadcast (Xabar yuborish)
* **Fayl:** `app/handlers/admins/buttons/button_admin.py`
* Botga start bosgan ammo **ro'yxatdan o'tmagan** foydalanuvchilarni integratsiya qilish uchun maxsus xabar yuborish tizimi.
* **Progress Tracking:** Har 20 ta yuborilgan xabarda admin panel dagi xabar holati yangilanib turadi.
* **Yakuniy statistika:** Muvaffaqiyatli yetkazilganlar, xatoliklar (bloklaganlar) va jami hisobot.

---

## 📁 Handlers Tizimi va Struktura

Loyiha arxitekturasi modullilik va tozalik prinsiplari asosida qayta tashkil etildi:

```text
app/handlers/
├── users/
│   ├── start.py          # Botni ishga tushirish va referal triggerlari
│   ├── register.py       # Bosqichma-bosqich ro'yxatdan o'tish logikasi
│   ├── menu.py           # Profil, reyting va targ'ibot menyulari
│   ├── test.py           # Test topshirish interfeysi va taymer translyatsiyasi
│   ├── help.py           # Yordam va yo'riqnomalar
│   └── prizes.py         # Sovrinlar ro'yxati va shartlar
└── admins/
    ├── main_admin.py     # Asosiy admin boshqaruv paneli
    ├── users.py          # Foydalanuvchilar bazasi va qidiruv
    ├── contest.py        # Konkurs boshqaruvi va Randomizer
    ├── settings_admin.py # Tizim va konfiguratsiya sozlamalari (YANGI)
    ├── ads/              # Reklama va kontent menejmenti
    ├── channels/         # Majburiy obunalar va kanallar nazorati
    ├── tests/
    │   └── test_admin.py # Test sozlamalari va statistika (YANGI)
    └── buttons/
        └── button_admin.py # Dinamik tugmalar va target-broadcast (YANGI)
