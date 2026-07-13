# Yemxona Biznesi — Smart Yem Qarz Daftari (Telegram Bot)

Yem-xashak (qopda yem) sotuvchisi uchun shaxsiy qarz va savdo hisobi boti.
**Faqat bitta owner (siz)** foydalanishi uchun — boshqalar kira olmaydi (Telegram ID orqali himoyalangan).

## Imkoniyatlari
- 👤 Mijoz qo'shish (ism, telefon, manzil, izoh)
- ➕ Savdo kiritish: summa + **nima olingan** (masalan "2 qop Start yem, 1 qop Rost")
- 💳 To'lov qabul qilish (qarz avtomatik kamayadi)
- ↩️ Qaytarish (mahsulot qaytganda qarz kamayadi)
- 🏷 Chegirma (qarz kamayadi)
- 📋 Qarzdorlar ro'yxati (qolgan qarz, qachon olgani)
- ⏰ Muddati o'tgan qarzlar
- 🔍 Mijoz qidirish (10-lab/100-lab mijoz uchun)
- 💱 Ikki valyuta: so'm va $ alohida, javob `"... so'm + ... $"` ko'rinishida
- 📊 Hisobot va 📥 Excel eksport

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
   ```
2. O'z Telegram ID'ingizni @userinfobot orqali bilib oling, `ALLOWED_USER_IDS` ga yozing.
3. `STRICT_MODE = True` qoldiring (boshqalar kira olmasin) — `config.py` da.

## Ishga tushirish
```bash
python bot.py
```

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
- SMS yuborish (Eskiz.uz / Playmobile API)
- Mahsulotlar ro'yxati (nomenklatura)
- Ombor qoldig'i
