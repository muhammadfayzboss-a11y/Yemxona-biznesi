# -*- coding: utf-8 -*-
"""
Smart Yem Qarz Daftari - Telegram bot (MVP)
Faqat bitta owner (siz) foydalanishi uchun.
Ikki valyuta: so'm va $ alohida saqlanadi, javob "... so'm + ... $" ko'rinishida.
"""

import asyncio
import os
import re
from datetime import datetime, timedelta

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
    b.button(text="📦 Mahsulot qo'shish")
    b.button(text="📋 Qarzdorlar")
    b.button(text="⏰ Muddati o'tganlar")
    b.button(text="📅 Bugun to'lash")
    b.button(text="🏆 Eng katta qarzdorlar")
    b.button(text="📅 Sana oralig'i")
    b.button(text="🔍 Mijoz qidirsh")
    b.button(text="🔍 Mahsulot qidirsh")
    b.button(text="📊 Hisobot")
    b.button(text="📩 SMS yuborish")
    b.button(text="📥 Excel yuklab olish")
    b.adjust(2, 2, 2, 2, 2, 2)
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
    data = await state.get_data()
    if data.get("product_mode"):
        # Mahsulot qo'shish rejimi
        names = [n.strip() for n in message.text.split(",") if n.strip()]
        added = 0
        for n in names:
            if db.add_product(n):
                added += 1
        await state.clear()
        if added:
            await message.answer(f"✅ {added} ta mahsulot qo'shildi.", reply_markup=main_kb())
        else:
            await message.answer("⚠️ Barcha mahsulotlar allaqachon mavjud yoki xato.", reply_markup=main_kb())
        return
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


# ---------------- Mahsulot qo'shish ----------------

@dp.message(F.text == "📦 Mahsulot qo'shish")
async def product_add(message: Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        return
    kb = ReplyKeyboardBuilder()
    kb.button(text="🔙 Bosh menyu")
    kb.adjust(1)
    await message.answer(
        "Yangi mahsulot nomini yozing (masalan: Start yem).\n"
        "Bir nechta bo'lsa vergul bilan: 'Start yem, Rost, Kafta'",
        reply_markup=kb.as_markup(resize_keyboard=True),
    )
    await state.set_state(AddClient.name)  # vaqtinchalik state sifatida foydalanamiz
    await state.update_data(product_mode=True)


# ---------------- Bugun to'lash kerak ----------------

@dp.message(F.text == "📅 Bugun to'lash")
async def due_today_h(message: Message):
    if not is_allowed(message.from_user.id):
        return
    rows = db.due_today()
    if not rows:
        await message.answer("✅ Bugun to'lash kerak bo'lgan qarzlar yo'q.")
        return
    text = "📅 *Bugun to'lash kerak:*\n\n"
    for c, u, d in rows:
        text += f"• *{c['name']}* — {fmt_money(u, d)}\n"
        if c["phone"]:
            text += f"   📞 {c['phone']}\n"
    await message.answer(text, parse_mode="Markdown")


# ---------------- Bosh menyuga qaytish ----------------

@dp.message(F.text == "🔙 Bosh menyu")
async def back_home(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Asosiy menyu:", reply_markup=main_kb())


# ---------------- Eng katta qarzdorlar ----------------

@dp.message(F.text == "🏆 Eng katta qarzdorlar")
async def top_debtors_h(message: Message):
    if not is_allowed(message.from_user.id):
        return
    rows = db.top_debtors(10)
    if not rows:
        await message.answer("✅ Qarzdorlar yo'q.")
        return
    text = "🏆 *Eng katta qarzdorlar (Top 10):*\n\n"
    for i, (c, u, d) in enumerate(rows, 1):
        text += f"{i}. *{c['name']}* — {fmt_money(u, d)}\n"
    await message.answer(text, parse_mode="Markdown")


# ---------------- Sana oralig'i hisoboti ----------------

class RangeReport(StatesGroup):
    start = State()
    end = State()


@dp.message(F.text == "📅 Sana oralig'i")
async def range_start(message: Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        return
    await state.set_state(RangeReport.start)
    await message.answer("Boshlang'ich sanani yozing (DD.MM.YYYY):")


@dp.message(RangeReport.start)
async def range_start_date(message: Message, state: FSMContext):
    d = parse_due(message.text.strip())
    if not d:
        await message.answer("❌ Sana noto'g'ri. DD.MM.YYYY ko'rinishida yozing:")
        return
    await state.update_data(start=d)
    await state.set_state(RangeReport.end)
    await message.answer("Oxirgi sanani yozing (DD.MM.YYYY):")


@dp.message(RangeReport.end)
async def range_end_date(message: Message, state: FSMContext):
    d = parse_due(message.text.strip())
    if not d:
        await message.answer("❌ Sana noto'g'ri. DD.MM.YYYY ko'rinishida yozing:")
        return
    data = await state.get_data()
    rep = db.range_report(data["start"], d)
    await state.clear()
    text = (
        f"📅 *{data['start']} → {d} hisoboti*\n\n"
        f"🛒 Savdo: {fmt_money(rep['sale_u'], rep['sale_d'])}\n"
        f"💰 To'lov: {fmt_money(rep['pay_u'], rep['pay_d'])}\n"
        f"📝 Operatsiyalar: {rep['count']}\n"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=main_kb())


# ---------------- Mahsulot qidirish ----------------

@dp.message(F.text == "🔍 Mahsulot qidirsh")
async def product_search_start(message: Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        return
    await state.set_state(SearchClient.query)
    await message.answer("Mahsulot nomini yozing (masalan: 'Start'):")


@dp.message(SearchClient.query)
async def search_do(message: Message, state: FSMContext):
    q = message.text.strip()
    # Mijoz qidiruvmi yoki mahsulot qidiruvmi? State'da belgilanadi.
    # Bu yerda oddiy: mijoz qidiruv uchun ishlatiladi, mahsulot uchun alohida state kerak.
    # Vaqtinchalik: ikkalasini ham qilamiz (mijoz topilsa ko'rsatamiz, mahsulot ham)
    rows_c = db.find_clients(q)
    rows_p = db.search_product_in_ops(q)
    await state.clear()
    text = f"🔍 *'{q}' bo'yicha:*\n\n"
    if rows_c:
        text += "*Mijozlar:*\n"
        for c in rows_c[:10]:
            u, d = db.get_client_balance(c["id"])
            text += f"• {c['name']} — {fmt_money(u, d)}\n"
    if rows_p:
        text += "\n*Operatsiyalar (mahsulot):*\n"
        for o in rows_p[:10]:
            amt = fmt_money(o["amount_uzs"] or 0, o["amount_usd"] or 0)
            text += f"• {o['client_name']}: {amt} ({o['product']}) — {o['created_at'][:10]}\n"
    if not rows_c and not rows_p:
        text += "❌ Topilmadi."
    await message.answer(text, parse_mode="Markdown")


# ---------------- SMS yuborish ----------------

@dp.message(F.text == "📩 SMS yuborish")
async def sms_start(message: Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        return
    debtors = db.debtors()
    if not debtors:
        await message.answer("Hozircha qarzdorlar yo'q.")
        return
    kb = InlineKeyboardBuilder()
    for c, u, d in debtors[:40]:
        kb.button(text=f"{c['name']} ({fmt_money(u,d)})", callback_data=f"smsclient_{c['id']}")
    kb.adjust(1)
    await state.set_state(AddPayment.client)
    await state.update_data(sms_mode=True)
    await message.answer("Qaysi mijozga SMS yuborish?", reply_markup=kb.as_markup())


@dp.callback_query(F.data.startswith("smsclient_"))
async def sms_select(callback: CallbackQuery, state: FSMContext):
    cid = int(callback.data.split("_")[1])
    c = db.get_client(cid)
    u, d = db.get_client_balance(cid)
    if not c["phone"]:
        await callback.message.edit_text(
            f"⚠️ {c['name']} da telefon raqami yo'q. Avval mijozga telefon raqamini qo'shing."
        )
        await callback.answer()
        await state.clear()
        return
    from sms import make_debt_message, send_sms, get_token
    shop_phone = os.getenv("SHOP_PHONE", "")
    msg = make_debt_message(c["name"], u, d, c.get("due_date"), shop_phone)
    await callback.message.edit_text(
        f"📩 Yuboriladigan SMS:\n\n{msg}\n\nYuborish uchun 'Ha' deb javob bering."
    )
    await state.update_data(sms_msg=msg, sms_phone=c["phone"])
    await callback.answer()


@dp.message(F.text.in_({"Ha", "ha", "HA", "✅ Ha"}))
async def sms_confirm(message: Message, state: FSMContext):
    data = await state.get_data()
    if "sms_msg" not in data:
        return
    from sms import send_sms, get_token
    token = os.getenv("ESKIZ_TOKEN") or get_token()
    res = send_sms(data["sms_phone"], data["sms_msg"], token=token)
    await state.clear()
    if res.get("status") == "success" or "id" in res:
        await message.answer("✅ SMS yuborildi.")
    else:
        await message.answer(f"❌ SMS yuborilmadi: {res.get('message', res)}")
    return


# ---------------- Mijoz tarixi ----------------

@dp.message(F.text == "📜 Mijoz tarixi")
async def history_start(message: Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        return
    clients = db.list_clients()
    if not clients:
        await message.answer("Avval mijoz qo'shing.")
        return
    kb = InlineKeyboardBuilder()
    for c in clients[:40]:
        kb.button(text=c["name"], callback_data=f"histclient_{c['id']}")
    kb.adjust(2)
    await message.answer("Mijozni tanlang:", reply_markup=kb.as_markup())


@dp.callback_query(F.data.startswith("histclient_"))
async def history_show(callback: CallbackQuery, state: FSMContext):
    cid = int(callback.data.split("_")[1])
    c = db.get_client(cid)
    ops = db.get_client_operations(cid)
    u, d = db.get_client_balance(cid)
    text = f"📜 *{c['name']} tarixi*\n"
    if c["phone"]:
        text += f"📞 {c['phone']}\n"
    text += f"💳 Qolgan qarz: *{fmt_money(u, d)}*\n\n"
    type_names = {
        "sale": "🛒 Savdo",
        "payment": "💰 To'lov",
        "return": "↩️ Qaytarish",
        "discount": "🏷 Chegirma",
    }
    for o in ops[:25]:
        tn = type_names.get(o["type"], o["type"])
        amt = fmt_money(o["amount_uzs"] or 0, o["amount_usd"] or 0)
        text += f"• {tn}: {amt}"
        if o["product"]:
            text += f" ({o['product']})"
        if o["due_date"]:
            text += f" [muddat: {o['due_date']}]"
        text += f" — {o['created_at'][:16]}\n"
    if len(ops) > 25:
        text += f"\n... va yana {len(ops)-25} ta operatsiya"
    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer()


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


async def auto_reminder(admin_id):
    """Har kuni kechqurun muddati yaqin/yetgan qarzdorlarga SMS yuborish.
    (Soddalashtirilgan: bot ishga tushganda va har 24 soatda ishlaydi)
    """
    from sms import make_debt_message, send_sms, get_token
    today = datetime.now().strftime("%Y-%m-%d")
    soon = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
    token = os.getenv("ESKIZ_TOKEN") or get_token()
    shop_phone = os.getenv("SHOP_PHONE", "")
    sent = 0
    for c, u, d, due in db.overdue_debtors(today=today):
        msg = make_debt_message(c["name"], u, d, due, shop_phone)
        if c["phone"] and token:
            res = send_sms(c["phone"], "⏰ MUDDATI O'TDI. " + msg, token=token)
            if res.get("status") == "success":
                sent += 1
    for c, u, d in db.due_today(today=soon):
        if c["phone"] and token:
            msg = make_debt_message(c["name"], u, d, soon, shop_phone)
            res = send_sms(c["phone"], "⏰ Muddat yaqinlashmoqda. " + msg, token=token)
            if res.get("status") == "success":
                sent += 1
    if sent:
        try:
            await bot.send_message(admin_id, f"📩 {sent} ta eslatma SMS yuborildi.")
        except Exception:
            pass


async def main():
    db.init_db()
    print("Bot ishga tushdi...")
    # Admin ID (birinchi ruxsat etilgan)
    admin_id = config.ALLOWED_USER_IDS[0] if config.ALLOWED_USER_IDS else None
    # Birinchi marta ishga tushganda avtomatik eslatma (ixtiyoriy)
    if admin_id and os.getenv("AUTO_REMINDER", "false").lower() == "true":
        asyncio.create_task(auto_reminder( 60 * 60 * 24))
    await dp.start_polling(bot)


def schedule_daily():
    """APScheduler orqali har kuni belgilangan vaqtda eslatma yuborish."""
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from sms import make_debt_message, send_sms, get_token
        sched = AsyncIOScheduler()
        admin_id = config.ALLOWED_USER_IDS[0] if config.ALLOWED_USER_IDS else None

        async def job():
            await auto_reminder(admin_id)

        if admin_id:
            sched.add_job(job, "cron", hour=19, minute=0)
            sched.start()
        return sched
    except ImportError:
        return None


if __name__ == "__main__":
    sched = schedule_daily()
    asyncio.run(main())
