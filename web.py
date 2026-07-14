# -*- coding: utf-8 -*-
"""
Web boshqaruv paneli (Flask).
Ishga tushirish: python web.py
Port: 5000 (yoki .env da WEB_PORT)
Faqat siz (ADMIN_IDS) kirasiz - oddiy parol orqali himoyalangan.
"""

import os
from flask import Flask, render_template_string, request, redirect, abort

import db
import config
from formats import fmt_money

app = Flask(__name__)

WEB_PASSWORD = os.getenv("WEB_PASSWORD", "admin123")
WEB_PORT = int(os.getenv("WEB_PORT", "5000"))
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")


def check_auth():
    # Soddalashtirilgan: parol so'raladi (GET ?pw= yoki cookie)
    pw = request.args.get("pw") or request.cookies.get("pw")
    return pw == WEB_PASSWORD


TEMPLATE = """
<!DOCTYPE html>
<html lang="uz">
<head>
<meta charset="utf-8">
<title>Yemxona - Boshqaruv paneli</title>
<style>
body{font-family:Arial;margin:20px;background:#f5f5f5}
.card{background:#fff;padding:15px;margin:10px 0;border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,.1)}
table{width:100%;border-collapse:collapse}
th,td{padding:8px;border:1px solid #ddd;text-align:left}
th{background:#2E7D32;color:#fff}
.btn{background:#2E7D32;color:#fff;padding:8px 12px;border:none;border-radius:4px;cursor:pointer;text-decoration:none;display:inline-block}
h2{color:#2E7D32}
</style>
</head>
<body>
<h1>📊 Yemxona Boshqaruv Paneli</h1>
<div class="card">
<a class="btn" href="/?pw={{pw}}">Qarzdorlar</a>
<a class="btn" href="/stock?pw={{pw}}">Ombor</a>
<a class="btn" href="/report?pw={{pw}}">Hisobot</a>
<a class="btn" href="/clients?pw={{pw}}">Mijozlar</a>
</div>

{% if page == 'debtors' %}
<h2>Qarzdorlar</h2>
<div class="card"><table>
<tr><th>#</th><th>Mijoz</th><th>Telefon</th><th>Qolgan qarz</th></tr>
{% for c,u,d in debtors %}
<tr><td>{{loop.index}}</td><td>{{c['name']}}</td><td>{{c['phone'] or ''}}</td><td>{{fmt_money(u,d)}}</td></tr>
{% endfor %}
</table></div>
{% endif %}

{% if page == 'stock' %}
<h2>Ombor qoldig'i</h2>
<div class="card"><table>
<tr><th>Mahsulot</th><th>Miqdor</th><th>Birlik</th></tr>
{% for r in stock %}
<tr><td>{{r['product_name']}}</td><td>{{r['qty']}}</td><td>{{r['unit']}}</td></tr>
{% endfor %}
</table></div>
{% endif %}

{% if page == 'report' %}
<h2>Umumiy hisobot</h2>
<div class="card">
<p>Jami savdo: {{fmt_money(rep_sale_u, rep_sale_d)}}</p>
<p>Jami to'lov: {{fmt_money(rep_pay_u, rep_pay_d)}}</p>
<p>Qarzdorlar soni: {{debtors|length}}</p>
</div>
{% endif %}

{% if page == 'clients' %}
<h2>Mijozlar</h2>
<div class="card"><table>
<tr><th>Ism</th><th>Telefon</th><th>Manzil</th><th>Qolgan qarz</th></tr>
{% for c in clients %}
<tr><td>{{c['name']}}</td><td>{{c['phone'] or ''}}</td><td>{{c['address'] or ''}}</td><td>{{fmt_money(c_debt[c['id']][0], c_debt[c['id']][1])}}</td></tr>
{% endfor %}
</table></div>
{% endif %}

</body>
</html>
"""


@app.route("/")
@app.route("/<page>")
def index(page="debtors"):
    if not check_auth():
        return redirect("/login")
    db.init_db()
    pw = request.args.get("pw", "")
    ctx = {"pw": pw, "page": page, "fmt_money": fmt_money}
    if page == "debtors":
        ctx["debtors"] = db.debtors()
    elif page == "stock":
        ctx["stock"] = db.list_stock()
    elif page == "report":
        ops = db.all_operations()
        su = sd = pu = pd = 0.0
        for o in ops:
            if o["type"] == "sale":
                su += o["amount_uzs"] or 0; sd += o["amount_usd"] or 0
            elif o["type"] == "payment":
                pu += o["amount_uzs"] or 0; pd += o["amount_usd"] or 0
        ctx["rep_sale_u"] = su; ctx["rep_sale_d"] = sd
        ctx["rep_pay_u"] = pu; ctx["rep_pay_d"] = pd
        ctx["debtors"] = db.debtors()
    elif page == "clients":
        clients = db.list_clients()
        c_debt = {c["id"]: db.get_client_balance(c["id"]) for c in clients}
        ctx["clients"] = clients
        ctx["c_debt"] = c_debt
    return render_template_string(TEMPLATE, **ctx)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("pw") == WEB_PASSWORD:
            # Oddiy: cookie orqali (xavfsizroq session kerak bo'lsa keyin)
            resp = redirect("/?pw=" + WEB_PASSWORD)
            resp.set_cookie("pw", WEB_PASSWORD)
            return resp
        return "❌ Noto'g'ri parol", 403
    return """
    <form method="post">
    <h2>🔐 Web panel paroli</h2>
    <input name="pw" type="password" placeholder="Parol">
    <button type="submit">Kirish</button>
    </form>
    """


if __name__ == "__main__":
    db.init_db()
    print(f"Web panel: http://localhost:{WEB_PORT}  (parol: {WEB_PASSWORD})")
    app.run(host=WEB_HOST, port=WEB_PORT, debug=False)
