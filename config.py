# -*- coding: utf-8 -*-
"""
Sozlamalar fayli.

XAVFSIZLIK: Tokenni to'g'ridan-to'g'ri shu yerga yozmang.
O'rniga `.env` fayl yarating va quyidagilarni yozing:
    BOT_TOKEN=your_token_here
    ALLOWED_USER_IDS=123456789

Agar .env topilmasa, quyidagi o'zgaruvchilar ishlatiladi (bo'sh qoldiring).
"""

import os

# .env dan o'qish (agar mavjud bo'lsa)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv o'rnatilmagan bo'lsa, xatolik bermaydi
    pass


# BotFather'dan olgan tokeningiz.
# .env fayldagi BOT_TOKEN dan olinadi, bo'lmasa pastdagi qiymat.
BOT_TOKEN = os.getenv("BOT_TOKEN", "BU_YERGA_BOT_TOKEN_YOZING")


def _parse_ids(raw):
    if not raw:
        return []
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


# FAQAT sizning Telegram ID'ingiz. Boshqalar botga kira olmaydi.
# .env dagi ALLOWED_USER_IDS="123456789, 987654321" ko'rinishida bo'lishi mumkin.
ALLOWED_USER_IDS = _parse_ids(os.getenv("ALLOWED_USER_IDS", "123456789"))


# Agar True bo'lsa, ro'yxatdan tashqari foydalanuvchilarga "Ruxsat yo'q" deb javob beriladi.
STRICT_MODE = True


# Bazaviy valyuta belgilari
UZS = "so'm"
USD = "$"
