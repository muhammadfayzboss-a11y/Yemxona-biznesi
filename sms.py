# -*- coding: utf-8 -*-
"""
Eskiz.uz SMS xizmati uchun integratsiya.
API hujjat: https://eskiz.uz/docs/api

.env faylida:
    ESKIZ_EMAIL=your@email.com
    ESKIZ_PASSWORD=your_password
    ESKIZ_FROM=SMS sender nomi (ixtiyoriy)

Yoki tayyor token bo'lsa:
    ESKIZ_TOKEN=your_eskiz_token
"""

import os
import json
import urllib.request
import urllib.parse
import base64

ESKIZ_BASE = "https://notify.eskiz.uz/api"


def _post(path, data, token=None):
    url = ESKIZ_BASE + path
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8"))
        except Exception:
            return {"status": "error", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_token(email=None, password=None):
    """Eskiz'dan API token olish. .env dan o'qiladi agar berilmasa."""
    if email is None:
        email = os.getenv("ESKIZ_EMAIL")
    if password is None:
        password = os.getenv("ESKIZ_PASSWORD")
    if not email or not password:
        return None
    res = _post("/auth/login", {"email": email, "password": password})
    if res.get("status") == "success" or "data" in res:
        token = res.get("data", {}).get("token")
        if token:
            # .env da saqlab qo'yish uchun (iyxtiyoriy)
            try:
                with open(".env", "a", encoding="utf-8") as f:
                    f.write(f"\nESKIZ_TOKEN={token}\n")
            except Exception:
                pass
        return token
    return None


def send_sms(phone, message, token=None, sender=None):
    """SMS yuborish.
    phone: +998901234567 ko'rinishida
    message: UTF-8 matn
    """
    if token is None:
        token = os.getenv("ESKIZ_TOKEN")
    if not token:
        token = get_token()
    if not token:
        return {"status": "error", "message": "Eskiz token topilmadi (.env da ESKIZ_TOKEN yoki ESKIZ_EMAIL/PASSWORD sozlang)"}
    if sender is None:
        sender = os.getenv("ESKIZ_FROM", "4546")
    # telefonni tozalash: faqat raqam
    phone = "".join(ch for ch in str(phone) if ch.isdigit())
    if phone.startswith("998") and len(phone) == 12:
        pass
    elif phone.startswith("8") and len(phone) == 9:
        phone = "998" + phone[1:]
    elif phone.startswith("0") and len(phone) == 9:
        phone = "998" + phone[1:]
    res = _post("/message/sms/send", {
        "mobile_phone": phone,
        "message": message,
        "from": sender,
    }, token=token)
    return res


def make_debt_message(client_name, debt_uzs, debt_usd, due_date=None, shop_phone=None):
    """Qarzdorga yuboriladigan xabar matni."""
    from formats import fmt_money
    debt = fmt_money(debt_uzs, debt_usd)
    msg = f"Assalomu alaykum, {client_name} aka. Sizning qarzingiz: {debt}."
    if due_date:
        msg += f" To'lov muddati: {due_date}."
    if shop_phone:
        msg += f" Batafsil: {shop_phone}"
    return msg


if __name__ == "__main__":
    # Test (token kerak bo'ladi)
    t = get_token()
    print("Token:", t)
    if t:
        r = send_sms("+998901234567", "Test xabar", token=t)
        print(r)
