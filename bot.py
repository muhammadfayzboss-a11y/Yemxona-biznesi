# -*- coding: utf-8 -*-
"""
Smart Yem Qarz Daftari - Telegram bot (MVP)
Faqat bitta owner (siz) foydalanishi uchun.
Ikki valyuta: so'm va $ alohida saqlanadi, javob "... so'm + ... $" ko'rinishida.
"""

import asyncio
import re
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

import config
import db
from formats import fmt_money, fmt_num


bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()


# ---------------- Ruxsat tekshiruvi ----------------

def is_allowed(user_id: int) -> bool:
    if not config.STRICT_MODE:
        return True
    return user_id in config.ALLOWED_USER_IDS


# ---------------- Klaviatura ----------------

def main_kb():
    b = ReplyKeyboardBuilder()
    b.button(text="➕ Savdo kiritish")
    b.button(text="💳 To'lov qabul qilish")
    b.button(text="↩️ Qaytarish")
    b.button(text="🏷 Chegirma")
    b.button(text="👤 Mijoz qo'shish")
    b.button(text="📋 Qarzdorlar")
    b.button(text="⏰ Muddati o'tganlar")
    b.button(text="🔍 Mijoz qidirsh")
    b.button(text="📊 Hisobot")
    b.button(text="📥 Excel yuklab olish")
    b.adjust(2, 2, 2, 2, 2)
    return b.as_markup(resize_keyboard=True)


# ---------------- Holatlar (FSM) ----------------

class AddClient(StatesGroup):
    name = State()
    phone = State()
    address = State()
    note = State()


class AddSale(StatesGroup):
    client = State()
    amount = State()
    product = State()
    due_date = State()


class AddPayment(StatesGroup):
    client = State()
    amount = State()
    note = State()


class SearchClient(StatesGroup):
    query = State()


class AddAdjust(StatesGroup):
    """Qaytarish yoki chegirma uchun umumiy holatlar."""
    otype = State()
    client = State()
    amount = State()
    note = State()


# ---------------- Yordamchi ----------------

def parse_money(text):
    """Matndan so'm va dollar miqdorini ajratib oladi.
    Qabul qiladi: '500.000', '500000', '500$', '500 $', '1.000.000 so'm',
    '300$ + 500000', '500 ming so\'m' (ming/ming so'zini 1000 ga ko'paytiradi).
    Qaytaradi: (uzs:float, usd:float)
    """
    text = text.replace(",", ".").lower()
    uzs = 0.0
    usd = 0.0

    # "ming" so'zini 1000 ga aylantiramiz
    def expand(thousands):
        return thousands * 1000

    # dollar qismi: raqam(lar) $ belgisi yoki 'dollar' so'zi bilan
    usd_patterns = [
        r"(\d[\d\.\s]*)\s*\$",
        r"(\d[\d\.\s]*)\s*dollar",
        r"\$\s*(\d[\d\.\s]*)",
    ]
    for pat in usd_patterns:
        m = re.search(pat, text)
        if m:
            num = m.group(1).replace(" ", "").replace(".", "")
            try:
                usd += float(num)
            except ValueError:
                pass
            text = text.replace(m.group(0), " ")

    # so'm qismi: qolgan raqamlar
    # "ming" so'zini hisobga olamiz
    # Avval "X ming" ni topamiz
    for m in re.finditer(r"(\d[\d\.\s]*)\s*ming", text):
        num = m.group(1).replace(" ", "").replace(".", "")
        try:
            uzs += expand(float(num))
        except ValueError:
            pass
        text = text.replace(m.group(0), " ")

    # qolgan oddiy raqamlar (so'm deb hisoblanadi)
    for m in re.finditer(r"\d[\d\.]*", text):
        s = m.group(0).replace(".", "")
        if s.isdigit() and len(s) >= 3:  # 3 xonali va undan katta -> so'm
            try:
                uzs += float(s)
            except ValueError:
                pass
    return uzs, usd


def parse_due(text):
    """Sanani turli formatdan (DD.MM.YYYY yoki DD.MM) SEquencega o'tkazadi."""
    text = text.strip()
    for fmt in ("%d.%m.%Y", "%d.%m", "%d/%m/%Y", "%d/%m"):
        try:
            dt = datetime.strptime(text, fmt)
            if dt.year == 1900:
                dt = dt.replace(year=datetime.now().year)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


# ---------------- /start ----------------

@dp.message(Command("start"))
async def cmd_start(message: Message):
    if not is_allowed(message.from_user.id):
        await message.answer("❌ Ruxsat yo'q. Bu bot faqat egasi uchun.")
        return
    await message.answer(
        "👋 *Smart Yem Qarz Daftari*\n\n"
        "Yem savdosi va qarzlarni boshqarish boti.\n"
        "Quyidagi tugmalardan foydalaning:",
        reply_markup=main_kb(),
        parse_mode="Markdown",
    )


# ---------------- Mijoz qo'shish ----------------

@dp.message(F.text == "👤 Mijoz qo'shish")
async def add_client_start(message: Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        return
    await state.set_state(AddClient.name)
    await message.answer("Mijozning ismini yozing:")


@dp.message(AddClient.name)
async def add_client_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AddClient.phone)
    await message.answer("Telefon raqami (ixtiyoriy, '-' yozing agar yo'q bo'lsa):")


@dp.message(AddClient.phone)
async def add_client_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    await state.update_data(phone=None if phone in ("-", "") else phone)
    await state.set_state(AddClient.address)
    await message.answer("Manzil (ixtiyoriy, '-' yozing):")


@dp.message(AddClient.address)
async def add_client_address(message: Message, state: FSMContext):
    addr = message.text.strip()
    await state.update_data(address=None if addr in ("-", "") else addr)
    await state.set_state(AddClient.note)
    await message.answer("Izoh (ixtiyoriy, '-' yozing):")


@dp.message(AddClient.note)
async def add_client_note(message: Message, state: FSMContext):
    note = message.text.strip()
    data = await state.get_data()
    note = None if note in ("-", "") else note
    cid = db.add_client(data["name"], data["phone"], data["address"], note)
    await state.clear()
    await message.answer(
        f"✅ Mijoz qo'shildi: *{data['name']}* (ID: {cid})",
        reply_markup=main_kb(),
        parse_mode="Markdown",
    )


# ---------------- Savdo kiritish ----------------

@dp.message(F.text == "➕ Savdo kiritish")
async def sale_start(message: Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        return
    clients = db.list_clients()
    if not clients:
        await message.answer("Avval mijoz qo'shing ('👤 Mijoz qo'shish').")
        return
    kb = InlineKeyboardBuilder()
    for c in clients[:40]:
        kb.button(text=c["name"], callback_data=f"selclient_{c['id']}")
    kb.adjust(2)
    await state.set_state(AddSale.client)
    await message.answer("Mijozni tanlang:", reply_markup=kb.as_markup())


@dp.callback_query(F.data.startswith("selclient_"))
async def sale_select_client(callback: CallbackQuery, state: FSMContext):
    cid = int(callback.data.split("_")[1])
    await state.update_data(client_id=cid)
    await state.set_state(AddSale.amount)
    await callback.message.edit_text(
        "Summani yozing. Misol:\n"
        "`500.000` yoki `500000` (so'm)\n"
        "`300$` yoki `300 $` (dollar)\n"
        "Aralash: `500000 + 100$`",
        parse_mode="Markdown",
    )
    await callback.answer()


@dp.message(AddSale.amount)
async def sale_amount(message: Message, state: FSMContext):
    uzs, usd = parse_money(message.text)
    if uzs == 0 and usd == 0:
        await message.answer("❌ Summani tushunmadim. Qaytadan yozing (masalan 500.000 yoki 300$):")
        return
    await state.update_data(amount_uzs=uzs, amount_usd=usd)
    await state.set_state(AddSale.product)
    await message.answer("Nima olinganini yozing (masalan: '2 qop Start yem, 1 qop Rost'):")


@dp.message(AddSale.product)
async def sale_product(message: Message, state: FSMContext):
    await state.update_data(product=message.text.strip())
    await state.set_state(AddSale.due_date)
    await message.answer("To'lash muddati (DD.MM.YYYY yoki DD.MM, ixtiyoriy '-'):")


@dp.message(AddSale.due_date)
async def sale_due(message: Message, state: FSMContext):
    txt = message.text.strip()
    due = None if txt in ("-", "") else parse_due(txt)
    if txt not in ("-", "") and due is None:
        await message.answer("❌ Sana noto'g'ri. DD.MM.YYYY ko'rinishida yozing yoki '-':")
        return
    data = await state.get_data()
    db.add_operation(
        data["client_id"], "sale",
        amount_uzs=data["amount_uzs"], amount_usd=data["amount_usd"],
        product=data["product"], due_date=due,
    )
    u, d = db.get_client_balance(data["client_id"])
    c = db.get_client(data["client_id"])
    await state.clear()
    await message.answer(
        f"✅ Savdo qo'shildi.\nMijoz: *{c['name']}*\n"
        f"Qolgan qarz: *{fmt_money(u, d)}*",
        reply_markup=main_kb(),
        parse_mode="Markdown",
    )


# ---------------- To'lov qabul qilish ----------------

@dp.message(F.text == "💳 To'lov qabul qilish")
async def pay_start(message: Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        return
    debtors = db.debtors()
    if not debtors:
        await message.answer("Hozircha qarzdorlar yo'q.")
        return
    kb = InlineKeyboardBuilder()
    for c, u, d in debtors[:40]:
        kb.button(text=f"{c['name']} ({fmt_money(u,d)})", callback_data=f"payclient_{c['id']}")
    kb.adjust(1)
    await state.set_state(AddPayment.client)
    await message.answer("Qaysi mijoz to'lov qildi?", reply_markup=kb.as_markup())


@dp.callback_query(F.data.startswith("payclient_"))
async def pay_select(callback: CallbackQuery, state: FSMContext):
    cid = int(callback.data.split("_")[1])
    await state.update_data(client_id=cid)
    await state.set_state(AddPayment.amount)
    await callback.message.edit_text(
        "To'lov summasini yozing (masalan `300.000` yoki `100$`):",
        parse_mode="Markdown",
    )
    await callback.answer()


@dp.message(AddPayment.amount)
async def pay_amount(message: Message, state: FSMContext):
    uzs, usd = parse_money(message.text)
    if uzs == 0 and usd == 0:
        await message.answer("❌ Summani tushunmadim. Qaytadan yozing:")
        return
    await state.update_data(amount_uzs=uzs, amount_usd=usd)
    await state.set_state(AddPayment.note)
    await message.answer("Izoh (ixtiyoriy, '-'):")


@dp.message(AddPayment.note)
async def pay_note(message: Message, state: FSMContext):
    note = message.text.strip()
    note = None if note in ("-", "") else note
    data = await state.get_data()
    db.add_operation(
        data["client_id"], "payment",
        amount_uzs=data["amount_uzs"], amount_usd=data["amount_usd"],
        note=note,
    )
    u, d = db.get_client_balance(data["client_id"])
    c = db.get_client(data["client_id"])
    await state.clear()
    await message.answer(
        f"✅ To'lov qabul qilindi.\nMijoz: *{c['name']}*\n"
        f"Qolgan qarz: *{fmt_money(u, d)}*",
        reply_markup=main_kb(),
        parse_mode="Markdown",
    )


# ---------------- Qaytarish / Chegirma ----------------

@dp.message(F.text.in_({"↩️ Qaytarish", "🏷 Chegirma"}))
async def adjust_start(message: Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        return
    debtors = db.debtors()
    if not debtors:
        await message.answer("Hozircha qarzdorlar yo'q.")
        return
    otype = "return" if message.text == "↩️ Qaytarish" else "discount"
    await state.update_data(otype=otype)
    label = "qaytarildi (mahsulot)" if otype == "return" else "chegirma"
    kb = InlineKeyboardBuilder()
    for c, u, d in debtors[:40]:
        kb.button(text=f"{c['name']} ({fmt_money(u,d)})", callback_data=f"adjclient_{c['id']}")
    kb.adjust(1)
    await state.set_state(AddAdjust.client)
    await message.answer(
        f"Qaysi mijoz uchun {label}? Tanlang:",
        reply_markup=kb.as_markup(),
    )


@dp.callback_query(F.data.startswith("adjclient_"))
async def adjust_select(callback: CallbackQuery, state: FSMContext):
    cid = int(callback.data.split("_")[1])
    await state.update_data(client_id=cid)
    await state.set_state(AddAdjust.amount)
    data = await state.get_data()
    label = "qaytarilgan summa" if data["otype"] == "return" else "chegirma summasi"
    await callback.message.edit_text(
        f"{label} ni yozing (masalan `300.000` yoki `100$`):",
        parse_mode="Markdown",
    )
    await callback.answer()


@dp.message(AddAdjust.amount)
async def adjust_amount(message: Message, state: FSMContext):
    uzs, usd = parse_money(message.text)
    if uzs == 0 and usd == 0:
        await message.answer("❌ Summani tushunmadim. Qaytadan yozing:")
        return
    await state.update_data(amount_uzs=uzs, amount_usd=usd)
    await state.set_state(AddAdjust.note)
    await message.answer("Izoh (ixtiyoriy, masalan 'buzilgan' yoki '-'):")


@dp.message(AddAdjust.note)
async def adjust_note(message: Message, state: FSMContext):
    note = message.text.strip()
    note = None if note in ("-", "") else note
    data = await state.get_data()
    db.add_operation(
        data["client_id"], data["otype"],
        amount_uzs=data["amount_uzs"], amount_usd=data["amount_usd"],
        note=note,
    )
    u, d = db.get_client_balance(data["client_id"])
    c = db.get_client(data["client_id"])
    action = "Qaytarish" if data["otype"] == "return" else "Chegirma"
    await state.clear()
    await message.answer(
        f"✅ {action} qo'shildi.\nMijoz: *{c['name']}*\n"
        f"Qolgan qarz: *{fmt_money(u, d)}*",
        reply_markup=main_kb(),
        parse_mode="Markdown",
    )


# ---------------- Qarzdorlar ----------------

@dp.message(F.text == "📋 Qarzdorlar")
async def list_debtors(message: Message):
    if not is_allowed(message.from_user.id):
        return
    debtors = db.debtors()
    if not debtors:
        await message.answer("✅ Qarzdorlar yo'q.")
        return
    text = "📋 *Qarzdorlar ro'yxati:*\n\n"
    for i, (c, u, d) in enumerate(debtors, 1):
        text += f"{i}. *{c['name']}* — {fmt_money(u, d)}\n"
        if c["phone"]:
            text += f"   📞 {c['phone']}\n"
    await message.answer(text, parse_mode="Markdown")


# ---------------- Muddati o'tganlar ----------------

@dp.message(F.text == "⏰ Muddati o'tganlar")
async def overdue(message: Message):
    if not is_allowed(message.from_user.id):
        return
    rows = db.overdue_debtors()
    if not rows:
        await message.answer("✅ Muddati o'tgan qarzlar yo'q.")
        return
    text = "⏰ *Muddati o'tgan qarzlar:*\n\n"
    for c, u, d, due in rows:
        text += f"• *{c['name']}* — {fmt_money(u, d)} (muddat: {due})\n"
    await message.answer(text, parse_mode="Markdown")


# ---------------- Qidiruv ----------------

@dp.message(F.text == "🔍 Mijoz qidirish")
async def search_start(message: Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        return
    await state.set_state(SearchClient.query)
    await message.answer("Mijoz ismi yoki telefon raqamini yozing:")


@dp.message(SearchClient.query)
async def search_do(message: Message, state: FSMContext):
    q = message.text.strip()
    rows = db.find_clients(q)
    await state.clear()
    if not rows:
        await message.answer("❌ Topilmadi.")
        return
    text = f"🔍 *'{q}' bo'yicha natijalar:*\n\n"
    for c in rows[:20]:
        u, d = db.get_client_balance(c["id"])
        text += f"• *{c['name']}* — {fmt_money(u, d)}\n"
        if c["phone"]:
            text += f"   📞 {c['phone']}\n"
        if c["address"]:
            text += f"   🏠 {c['address']}\n"
    await message.answer(text, parse_mode="Markdown")


# ---------------- Hisobot ----------------

@dp.message(F.text == "📊 Hisobot")
async def report(message: Message):
    if not is_allowed(message.from_user.id):
        return
    ops = db.all_operations()
    total_sale_u = total_sale_d = 0.0
    total_pay_u = total_pay_d = 0.0
    for o in ops:
        if o["type"] == "sale":
            total_sale_u += o["amount_uzs"] or 0
            total_sale_d += o["amount_usd"] or 0
        elif o["type"] == "payment":
            total_pay_u += o["amount_uzs"] or 0
            total_pay_d += o["amount_usd"] or 0
    debtors = db.debtors()
    debt_u = sum(u for _, u, _ in debtors)
    debt_d = sum(d for _, _, d in debtors)

    text = (
        "📊 *Umumiy hisobot*\n\n"
        f"💰 Jami savdo: {fmt_money(total_sale_u, total_sale_d)}\n"
        f"💳 Jami to'lov: {fmt_money(total_pay_u, total_pay_d)}\n"
        f"📋 Qarzdorlar soni: {len(debtors)}\n"
        f"⚠️ Qolgan qarz: {fmt_money(debt_u, debt_d)}\n"
    )
    await message.answer(text, parse_mode="Markdown")


# ---------------- Excel ----------------

@dp.message(F.text == "📥 Excel yuklab olish")
async def excel_export(message: Message):
    if not is_allowed(message.from_user.id):
        return
    try:
        import export_excel
        path = export_excel.export()
    except Exception as e:
        await message.answer(f"❌ Excel yaratishda xatolik: {e}")
        return
    await message.answer_document(document=open(path, "rb"),
                                  caption="📥 Qarzlar hisoboti (Excel)")


# ---------------- Oddiy matn (mijoz tanlash uchun emas) ----------------

@dp.message(Command("help"))
async def cmd_help(message: Message):
    if not is_allowed(message.from_user.id):
        return
    await message.answer(
        "Bot buyruqlari:\n"
        "/start - asosiy menyu\n"
        "/help - yordam\n\n"
        "Menyudan foydalaning.",
        reply_markup=main_kb(),
    )


async def main():
    db.init_db()
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
