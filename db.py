# -*- coding: utf-8 -*-
"""
Ma'lumotlar bazasi (SQLite).
Har bir operatsiya alohida yoziladi (savdo, to'lov, qaytarish, chegirma),
shunda qolgan qarz har doim hisoblanib chiqariladi va to'liq tarix saqlanadi.
"""

import sqlite3
from datetime import datetime

DB_PATH = "yem_qarz.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # Mijozlar jadvali
    cur.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        address TEXT,
        note TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )
    """)

    # Mahsulotlar ro'yxati (nomenklatura)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        unit TEXT DEFAULT 'qop',
        note TEXT
    )
    """)

    # Operatsiyalar jadvali. type: 'sale', 'payment', 'return', 'discount'
    # amount_uzs / amount_usd - shu operatsiyaning valyutaga qarab qismi.
    # Mahsulot (nima olingan) matn sifatida saqlanadi.
    cur.execute("""
    CREATE TABLE IF NOT EXISTS operations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        amount_uzs REAL DEFAULT 0,
        amount_usd REAL DEFAULT 0,
        product TEXT,
        due_date TEXT,
        note TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (client_id) REFERENCES clients(id)
    )
    """)

    conn.commit()
    conn.close()


# ---------------- Mijozlar ----------------

def add_client(name, phone=None, address=None, note=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO clients (name, phone, address, note) VALUES (?,?,?,?)",
        (name, phone, address, note),
    )
    cid = cur.lastrowid
    conn.commit()
    conn.close()
    return cid


def find_clients(query):
    """Ism/telefon bo'yicha qidiruv (10-lab/100-lab mijoz uchun)."""
    conn = get_conn()
    cur = conn.cursor()
    like = f"%{query}%"
    cur.execute(
        "SELECT * FROM clients WHERE name LIKE ? OR phone LIKE ? ORDER BY name LIMIT 50",
        (like, like),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def list_clients():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM clients ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return rows


def get_client(cid):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM clients WHERE id=?", (cid,))
    row = cur.fetchone()
    conn.close()
    return row


# ---------------- Operatsiyalar ----------------

def add_operation(client_id, otype, amount_uzs=0, amount_usd=0,
                  product=None, due_date=None, note=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO operations
           (client_id, type, amount_uzs, amount_usd, product, due_date, note)
           VALUES (?,?,?,?,?,?,?)""",
        (client_id, otype, amount_uzs, amount_usd, product, due_date, note),
    )
    oid = cur.lastrowid
    conn.commit()
    conn.close()
    return oid


def get_client_balance(cid):
    """Qolgan qarzni hisoblab chiqarish.
    Savdo + qaytarilgan (minus) - to'lov - chegirma.
    UZS va USD alohida hisoblanadi va alohida qaytariladi.
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM operations WHERE client_id=?", (cid,))
    rows = cur.fetchall()
    conn.close()

    debt_uzs = 0.0
    debt_usd = 0.0
    for r in rows:
        t = r["type"]
        u = r["amount_uzs"] or 0
        d = r["amount_usd"] or 0
        if t == "sale":
            debt_uzs += u
            debt_usd += d
        elif t == "payment":
            debt_uzs -= u
            debt_usd -= d
        elif t == "return":      # mahsulot qaytarildi -> qarz kamayadi
            debt_uzs -= u
            debt_usd -= d
        elif t == "discount":   # chegirma -> qarz kamayadi
            debt_uzs -= u
            debt_usd -= d
    return debt_uzs, debt_usd


def get_client_operations(cid):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM operations WHERE client_id=? ORDER BY created_at DESC, id DESC",
        (cid,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def debtors():
    """Qarzi bor barcha mijozlar (UZS yoki USD qolgan bo'lsa)."""
    clients = list_clients()
    result = []
    for c in clients:
        u, d = get_client_balance(c["id"])
        if u > 0.0001 or d > 0.0001:
            result.append((c, u, d))
    # Eng katta qarzdorlar tepada (so'm bo'yicha)
    result.sort(key=lambda x: x[1], reverse=True)
    return result


def overdue_debtors(today=None):
    """Muddati o'tgan qarzlar (due_date < bugungi sana va qarz qolgan)."""
    if today is None:
        today = datetime.now().strftime("%Y-%m-%d")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT o.client_id, o.due_date
           FROM operations o
           WHERE o.due_date IS NOT NULL AND o.due_date < ?
           GROUP BY o.client_id""",
        (today,),
    )
    rows = cur.fetchall()
    conn.close()
    result = []
    for r in rows:
        c = get_client(r["client_id"])
        if c is None:
            continue
        u, d = get_client_balance(c["id"])
        if u > 0.0001 or d > 0.0001:
            result.append((c, u, d, r["due_date"]))
    return result


def due_today(today=None):
    if today is None:
        today = datetime.now().strftime("%Y-%m-%d")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT DISTINCT client_id FROM operations WHERE due_date = ?",
        (today,),
    )
    rows = cur.fetchall()
    conn.close()
    result = []
    for r in rows:
        c = get_client(r["client_id"])
        if c is None:
            continue
        u, d = get_client_balance(c["id"])
        if u > 0.0001 or d > 0.0001:
            result.append((c, u, d))
    return result


def all_operations():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT o.*, c.name as client_name FROM operations o "
        "LEFT JOIN clients c ON c.id=o.client_id ORDER BY o.created_at DESC, o.id DESC",
    )
    rows = cur.fetchall()
    conn.close()
    return rows


# ---------------- Mahsulotlar (nomenklatura) ----------------

def add_product(name, unit="qop", note=None):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO products (name, unit, note) VALUES (?,?,?)",
            (name.strip(), unit, note),
        )
        pid = cur.lastrowid
        conn.commit()
        conn.close()
        return pid
    except sqlite3.IntegrityError:
        conn.close()
        return None  # allaqachon bor


def list_products():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return rows


def find_products(query):
    conn = get_conn()
    cur = conn.cursor()
    like = f"%{query}%"
    cur.execute("SELECT * FROM products WHERE name LIKE ? ORDER BY name LIMIT 20", (like,))
    rows = cur.fetchall()
    conn.close()
    return rows
