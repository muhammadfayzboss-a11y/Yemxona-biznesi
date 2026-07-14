# Yemxona Biznesi — Smart Yem Qarz Daftari (Telegram Bot)

Yem-xashak (qopda yem) sotuvchisi uchun shaxsiy qarz va savdo hisobi boti.
**Faqat bitta owner (siz)** foydalanishi uchun — boshqalar kira olmaydi (Telegram ID orqali himoyalangan).

## Imkoniyatlari
- 👤 Mijoz qo'shish (ism, telefon, manzil, izoh)
- ➕ Savdo kiritish: summa + **nima olingan** (masalan "2 qop Start yem, 1 qop Rost")
- 💳 To'lov qabul qilish (qarz avtomatik kamayadi)
- ↩️ Qaytarish (mahsulot qaytganda qarz kamayadi)
- 🏷 Chegirma (qarz kamayadi)
- 📦 **Mahsulotlar ro'yxati** (nomenklatura: Start yem, Rost, va h.k.)
- 📋 Qarzdorlar ro'yxati (qolgan qarz, qachon olgani)
- ⏰ Muddati o'tgan qarzlar
- 📅 Bugun to'lash keraklar
- 🏆 **Eng katta qarzdorlar** (Top-10)
- 📅 **Sana oralig'i hisoboti** (ikki sana orasidagi savdo/to'lov)
- 🔍 Mijoz qidirish (10-lab/100-lab mijoz uchun)
- 🔍 **Mahsulot qidirish** (qaysi mijoz qancha olgan)
- 📜 Mijoz tarixi (barcha savdo/to'lovlar)
- 📊 **Oylik hisobot**
- 🗑 Mijoz o'chirish (xato bo'lsa)
- 📩 **SMS yuborish** (Eskiz.uz orqali qarzdorga xabar)
- ⏰ Avtomatik eslatma (muddati yaqinlashganda/o'tganda SMS)
- 💱 Ikki valyuta: so'm va $ alohida, javob `"... so'm + ... $"` ko'rinishida
- 📥 Excel eksport

## O'rnatish
```bash
pip install -r requirements.txt
pip install openpyxl   # Excel uchun
```

## Sozlash
1. `.env` fayl yarating (`.env.example` ni nusxalang):
   ```
   BOT_TOKEN=your_bot_token_from_botfather
   ALLOWED_USER_IDS=123456789
   ESKIZ_EMAIL=your@email.com
   ESKIZ_PASSWORD=your_password
   SHOP_PHONE=+998901234567
   AUTO_REMINDER=false
   ```
2. O'z Telegram ID'ingizni @userinfobot orqali bilib oling, `ALLOWED_USER_IDS` ga yozing.
3. `STRICT_MODE = True` qoldiring (boshqalar kira olmasin) — `config.py` da.

## Ishga tushirish
```bash
python bot.py
```

## SMS (Eskiz.uz)
- [eskiz.uz](https://eskiz.uz) da ro'yxatdan o'ting, hamyonni to'ldiring.
- SMS yuboruvchi nomini (`from`) ro'yxatdan o'tkazing.
- `.env` da `ESKIZ_EMAIL` / `ESKIZ_PASSWORD` yoki tayyor `ESKIZ_TOKEN` yozing.
- "📩 SMS yuborish" tugmasi orqali qarzdorga xabar yuborasiz.
- `AUTO_REMINDER=true` qilsangiz, har kuni 19:00 da muddati yaqin/o'tganlarga avtomatik SMS boradi.

## Valyuta qanday kiritiladi?
- `500.000` yoki `500000` → so'm
- `300$` yoki `300 $` → dollar
- Aralash: `500000 + 100$`
- `500 ming so'm` → 500 000 so'm

Qolgan qarz har doim hisoblanib chiqariladi va `... so'm + ... $` ko'rinishida ko'rsatiladi.

## Ma'lumotlar qayerda?
SQLite bazasida (`yem_qarz.db`). Har bir operatsiya alohida yoziladi, shuning uchun qarz adashmaydi va to'liq tarix saqlanadi.

## Keyingi bosqichlar (keyin qo'shiladi)
- Web boshqaruv paneli
- Ombor qoldig'i
- Chek yoki qarz tilxati (PDF)
