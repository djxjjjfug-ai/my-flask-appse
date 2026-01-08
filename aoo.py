from flask import Flask, request, session, redirect, url_for, render_template_string
import sqlite3
import requests
import os

app = Flask(__name__)
app.secret_key = "pirate_server_24h_edition"

# ===== إعدادات الـ API بالمفتاح الجديد =====
API_URL = "https://smmvolt.com/api/v2"
API_KEY = "4a95df15071681dbb82f1374b4a0e2d6" 
SERVICE_ID = 2197 
PRICE_PER_1000 = 15 

# ===== إدارة قاعدة البيانات مع التحديث التلقائي =====
def init_db():
    db_path = os.path.join(os.getcwd(), "users.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, 
        password TEXT, balance REAL DEFAULT 0, is_admin INTEGER DEFAULT 0)""")
    c.execute("""CREATE TABLE IF NOT EXISTS deposits (
        id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, 
        sender_number TEXT, amount REAL, status TEXT DEFAULT 'قيد المراجعة')""")
    
    # حل مشكلة OperationalError تلقائياً
    try: c.execute("ALTER TABLE deposits ADD COLUMN sender_number TEXT")
    except: pass

    # حساب الأدمن (يوزر: admin / باسورد: 0999)
    c.execute("INSERT OR IGNORE INTO users (username, password, balance, is_admin) VALUES (?,?,?,?)", 
              ("admin", "0999", 0, 1))
    conn.commit()
    conn.close()

init_db()

def get_db():
    conn = sqlite3.connect("users.db")
    conn.row_factory = sqlite3.Row
    return conn

# ===== واجهات العرض (HTML) =====

login_design = """
<!DOCTYPE html><html><head><style>
body{font-family:Arial;background:#0f172a;color:white;text-align:center;}
.box{background:#1e293b;width:320px;margin:100px auto;padding:30px;border-radius:15px;border:2px solid orange;}
input{width:90%;padding:12px;margin:10px 0;border-radius:10px;border:1px solid #334155;background:#0f172a;color:white;}
button{padding:12px;background:orange;border:none;color:white;border-radius:10px;cursor:pointer;width:98%;font-weight:bold;}
</style></head><body>
<div class="box">
    <h2 style="color:orange;">🏴‍☠️ نظام القرصان</h2>
    <form method="post" autocomplete="off">
        <input type="text" name="srv_user" placeholder="اسم المستخدم" autocomplete="new-password" required>
        <input type="password" name="srv_pass" placeholder="كلمة المرور" autocomplete="new-password" required>
        <button type="submit">دخول</button>
    </form>
</div></body></html>
"""

waiting_design = """
<!DOCTYPE html><html><head><style>
body{font-family:Arial;background:#0f172a;color:white;text-align:center;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;}
.card{background:#1e293b; padding:40px; border-radius:20px; border:2px solid orange;}
.loader { border: 5px solid #f3f3f3; border-top: 5px solid orange; border-radius: 50%; width: 50px; height: 50px; animation: spin 1s linear infinite; margin: 20px auto; }
@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
</style><meta http-equiv="refresh" content="5;url=/dashboard"></head><body>
<div class="card"><div class="loader"></div><h2 style="color:orange;">جاري المعالجة...</h2><p>انتظر بضع دقائق وسيتم إضافة الرصيد لحسابك.</p></div></body></html>
"""

# ===== المسارات المنطقية =====

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("srv_user").strip()
        p = request.form.get("srv_pass").strip()
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username=?", (u,)).fetchone()
        if not user:
            db.execute("INSERT INTO users (username, password, balance, is_admin) VALUES (?,?,?,?)", (u, p, 0, 0))
            db.commit()
            user = db.execute("SELECT * FROM users WHERE username=?", (u,)).fetchone()
        session["user"] = user['username']
        session["admin"] = user['is_admin']
        db.close()
        return redirect(url_for("dashboard"))
    return render_template_string(login_design)

@app.route("/dashboard")
def dashboard():
    if "user" not in session: return redirect("/")
    db = get_db()
    row = db.execute("SELECT balance FROM users WHERE username=?", (session["user"],)).fetchone()
    db.close()
    return render_template_string("""
    <!DOCTYPE html><html><head><style>body{font-family:Arial;background:#0f172a;color:white;text-align:center;} 
    .btn{color:orange; margin:10px; text-decoration:none; border:2px solid orange; padding:12px; border-radius:10px; display:inline-block; font-weight:bold; width:200px;}</style></head><body>
    <h2 style="margin-top:50px;">أهلاً {{user}}</h2>
    <h1 style="color:yellow;">رصيدك: {{balance}} ج.م</h1>
    <a href="/add_balance" class="btn">💰 شحن رصيد</a><br>
    <a href="/order" class="btn">⚡ طلب نقاط (API)</a><br>
    {% if admin == 1 %}<a href="/admin" class="btn" style="background:red; color:white; border:none;">🏴‍☠️ لوحة الإدارة</a>{% endif %}
    <br><a href="/logout" style="color:gray; text-decoration:none; margin-top:20px; display:block;">🚪 خروج</a></body></html>""", user=session["user"], balance=row['balance'], admin=session.get("admin"))

@app.route("/add_balance", methods=["GET", "POST"])
def add_balance():
    if "user" not in session: return redirect("/")
    if request.method == "POST":
        db = get_db()
        db.execute("INSERT INTO deposits (username, sender_number, amount) VALUES (?,?,?)", 
                  (request.form['u_tag'], request.form['s_num'], float(request.form['amt'])))
        db.commit()
        db.close()
        return render_template_string(waiting_design)
    return render_template_string("""
    <!DOCTYPE html><html><head><style>body{font-family:Arial;background:#0f172a;color:white;text-align:center;} input{width:80%; padding:10px; margin:5px; border-radius:5px; background:#1e293b; color:white; border:1px solid #334155;}</style></head><body>
    <h2>💰 شحن فودافون كاش</h2><p>حول للرقم: <b style="color:yellow;">01091805870</b></p>
    <form method="post"><input name="u_tag" placeholder="أكد يوزر حسابك"><br><input name="s_num" placeholder="رقم المحفظة"><br><input name="amt" type="number" placeholder="المبلغ"><br><button style="background:green; color:white; padding:10px; border:none; border-radius:5px; cursor:pointer;">إرسال البيانات</button></form>
    </body></html>""")

@app.route("/order", methods=["GET", "POST"])
def order():
    if "user" not in session: return redirect("/")
    msg = ""
    if request.method == "POST":
        link = request.form.get("link")
        qty = int(request.form.get("qty"))
        cost = (qty / 1000) * PRICE_PER_1000
        db = get_db()
        user = db.execute("SELECT balance FROM users WHERE username=?", (session["user"],)).fetchone()
        if user['balance'] < cost:
            msg = "❌ رصيدك لا يكفي"
        else:
            payload = {'key': API_KEY, 'action': 'add', 'service': SERVICE_ID, 'link': link, 'quantity': qty}
            try:
                res = requests.post(API_URL, data=payload).json()
                if 'order' in res:
                    db.execute("UPDATE users SET balance = balance - ? WHERE username=?", (cost, session["user"]))
                    db.commit()
                    msg = f"✅ نجح الطلب! رقم: {res['order']}"
                else:
                    msg = f"❌ خطأ من الموقع: {res.get('error')}"
            except:
                msg = "❌ فشل الاتصال بالـ API"
        db.close()
    return render_template_string("""
    <!DOCTYPE html><html><head><style>body{font-family:Arial;background:#0f172a;color:white;text-align:center;} input{width:80%; padding:10px; margin:5px; border-radius:5px;}</style></head><body>
    <h2>⚡ طلب خدمات API</h2><form method="post"><input name="link" placeholder="الرابط"><br><input name="qty" type="number" placeholder="الكمية"><br><button style="background:orange; color:white; padding:10px; border:none; cursor:pointer; border-radius:5px;">تنفيذ</button></form>
    <p style="color:yellow;">{{msg}}</p><a href="/dashboard" style="color:orange;">رجوع</a></body></html>""", msg=msg)

@app.route("/admin")
def admin_panel():
    if session.get("admin") != 1: return redirect("/")
    db = get_db()
    users = db.execute("SELECT * FROM users").fetchall()
    deposits = db.execute("SELECT * FROM deposits ORDER BY id DESC").fetchall()
    db.close()
    return render_template_string("""
    <!DOCTYPE html><html><head><style>body{font-family:Arial;background:#0f172a;color:white;text-align:center; padding:10px;} table{width:100%; border-collapse:collapse; background:#1e293b;} th, td{border:1px solid #334155; padding:8px;} th{background:red;}</style></head><body>
    <h1>🏴‍☠️ لوحة القرصان</h1>
    <h3>👥 إدارة الحسابات</h3>
    <table><tr><th>المستخدم</th><th>الرصيد</th><th>شحن</th></tr>
    {% for u in users %}<tr><td>{{u.username}}</td><td>{{u.balance}}</td><td><form method="post" action="/admin/update"><input type="hidden" name="target" value="{{u.username}}"><input name="amt" style="width:40px;"><button>✅</button></form></td></tr>{% endfor %}
    </table>
    <h3>📱 طلبات الشحن</h3>
    <table><tr><th>المستخدم</th><th>الرقم</th><th>المبلغ</th></tr>
    {% for d in deposits %}<tr><td>{{d.username}}</td><td>{{d.sender_number}}</td><td>{{d.amount}}</td></tr>{% endfor %}
    </table><br><a href="/dashboard" style="color:orange;">رجوع</a></body></html>""", users=users, deposits=deposits)

@app.route("/admin/update", methods=["POST"])
def admin_update():
    if session.get("admin") != 1: return redirect("/")
    db = get_db()
    db.execute("UPDATE users SET balance = balance + ? WHERE username=?", (float(request.form['amt']), request.form['target']))
    db.commit()
    db.close()
    return redirect("/admin")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    # تم تغيير host لكي يعمل كخادم متاح للهواتف الأخرى
    app.run(host='0.0.0.0', port=5000)