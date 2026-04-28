# -*- coding: utf-8 -*-
from flask import Flask, render_template_string, request, redirect, session, url_for
from supabase import create_client
import sys
import io
import os
from dotenv import load_dotenv

load_dotenv() # لقراءة الملف


# إعداد الترميز للعربية
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

app = Flask(__name__)

# جلب البيانات من ملف env.py مباشرة
app.secret_key = os.getenv("SECRET_KEY")

URL = os.getenv("SUPABASE_URL")
KEY = os.getenv("SUPABASE_KEY")
ADMIN_USER = os.getenv("ADMIN_USER")
ADMIN_PASS = os.getenv("ADMIN_PASS")

# الاتصال بسوبابيس
supabase = create_client(URL, KEY)

STORE_NAME = "متجر 🌟"

STYLE = """
<style>
    :root { --primary: #6c5ce7; --bg: #f9f9f9; }
    body { font-family: 'Segoe UI', Tahoma; background: var(--bg); margin: 0; direction: rtl; text-align: right; }
    .navbar { background: var(--primary); color: white; padding: 15px; display: flex; justify-content: space-between; align-items: center; }
    .container { padding: 20px; display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; }
    .card { background: white; border-radius: 12px; width: 250px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); overflow: hidden; text-align: center; }
    .card img { width: 100%; height: 180px; object-fit: cover; }
    .btn-main { background: var(--primary); color: white; border: none; padding: 10px; border-radius: 8px; cursor: pointer; width: 90%; margin: 10px; font-weight: bold; text-decoration: none; display: inline-block; }
    .cart-float { position: fixed; bottom: 20px; left: 20px; background: var(--primary); color: white; width: 55px; height: 55px; border-radius: 50%; display: flex; justify-content: center; align-items: center; text-decoration: none; font-size: 24px; z-index: 1000; }
    .admin-card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 15px; border-right: 5px solid var(--primary); }
    input { padding: 8px; margin: 5px 0; border: 1px solid #ddd; border-radius: 6px; width: 100%; box-sizing: border-box; }
    .btn-del { background: #ff7675; color: white; border: none; padding: 5px 10px; border-radius: 5px; cursor: pointer; }
    .btn-edit { background: #00cec9; color: white; border: none; padding: 5px 10px; border-radius: 5px; cursor: pointer; }
</style>
"""

@app.route('/')
def index():
    products = supabase.table("products").select("*").execute().data
    cart_count = len(session.get('cart', []))
    return render_template_string(STYLE + """
    <nav class="navbar"><h2>{{ name }}</h2><a href="/login" style="color:white; text-decoration:none;">الإدارة</a></nav>
    <div class="container">
        {% for p in products %}
        <div class="card">
            <img src="{{ p.image_url }}">
            <h3>{{ p.name }}</h3>
            <p style="color:var(--primary); font-weight:bold;">{{ p.price }} د.ل</p>
            <form action="/add_to_cart" method="POST"><input type="hidden" name="p_id" value="{{ p.id }}"><button type="submit" class="btn-main">إضافة للسلة +</button></form>
        </div>
        {% endfor %}
    </div>
    <a href="/cart" class="cart-float">🛒<span style="position:absolute; top:0; right:0; background:red; border-radius:50%; padding:2px 6px; font-size:10px;">{{ count }}</span></a>
    """, name=STORE_NAME, products=products, count=cart_count)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    p_id = request.form.get('p_id')
    if 'cart' not in session: session['cart'] = []
    session['cart'].append(p_id)
    session.modified = True
    return redirect('/')

@app.route('/remove_from_cart/<int:index>')
def remove_from_cart(index):
    if 'cart' in session:
        cart = session['cart']
        if 0 <= index < len(cart):
            cart.pop(index)
            session.modified = True
    return redirect('/cart')

@app.route('/cart')
def view_cart():
    cart_ids = session.get('cart', [])
    if not cart_ids: return STYLE + "<div style='text-align:center; padding:50px;'><h2>السلة فارغة! 🛒</h2><a href='/'>ارجع للمتجر</a></div>"
    products_data = supabase.table("products").select("*").in_("id", cart_ids).execute().data
    
    display_items = []
    total = 0
    for idx, cid in enumerate(cart_ids):
        for item in products_data:
            if str(item['id']) == str(cid):
                total += float(item['price'])
                display_items.append({'name': item['name'], 'price': item['price'], 'index': idx})

    return render_template_string(STYLE + """
    <div style="max-width:500px; margin:40px auto; background:white; padding:20px; border-radius:12px; box-shadow:0 0 10px rgba(0,0,0,0.1);">
        <h2 style="text-align:center;">سلة المشتريات 🛒</h2>
        {% for item in items %}
        <div style="display:flex; justify-content:space-between; padding:10px 0; border-bottom:1px solid #eee; align-items:center;">
            <span>{{ item.name }} - {{ item.price }} د.ل</span>
            <a href="/remove_from_cart/{{ item.index }}" style="color:red; text-decoration:none; font-size:12px;">❌ حذف</a>
        </div>
        {% endfor %}
        <h3 style="text-align:center;">الإجمالي: {{ total }} د.ل</h3>
        <a href="/checkout" class="btn-main" style="background:#2ecc71; text-align:center;">تأكيد الطلب</a>
        <a href="/" style="display:block; text-align:center; color:gray; text-decoration:none; margin-top:10px;">مواصلة التسوق</a>
    </div>
    """, items=display_items, total=total)

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST':
        order_data = {
            "customer_name": request.form.get('name'),
            "phone": request.form.get('phone'),
            "address": request.form.get('address'),
            "items": str(session.get('cart', [])),
            "status": "New"
        }
        supabase.table("orders").insert(order_data).execute()
        session['cart'] = []
        return "<h1>تم استلام طلبك! 🎉</h1><a href='/'>العودة للمتجر</a>"
    return render_template_string(STYLE + '<div style="max-width:400px; margin:50px auto; background:white; padding:20px;"><form method="POST"><h2>بيانات التوصيل</h2><input name="name" placeholder="الاسم" required><input name="phone" placeholder="رقم الهاتف" required><textarea name="address" placeholder="العنوان"></textarea><button type="submit" class="btn-main" style="background:#2ecc71;">إرسال</button></form></div>')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('user') == ADMIN_USER and request.form.get('pass') == ADMIN_PASS:
            session['logged_in'] = True
            return redirect('/admin')
    return render_template_string(STYLE + '<div style="max-width:300px; margin:100px auto; background:white; padding:20px; border-radius:10px; text-align:center;"><form method="POST"><h2>دخول الإدارة 🔐</h2><input name="user" placeholder="اليوزر"><input type="password" name="pass" placeholder="الباسورد"><button type="submit" class="btn-main">دخول</button></form></div>')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('logged_in'): return redirect('/login')
    
    try:
        if request.method == 'POST':
            if 'add_p' in request.form:
                supabase.table("products").insert({
                    "name": request.form.get('n'), 
                    "price": request.form.get('p'), 
                    "image_url": request.form.get('img')
                }).execute()
            
            elif 'del_p' in request.form:
                p_id = request.form.get('id')
                supabase.table("products").delete().eq("id", p_id).execute()
            
            elif 'edit_p' in request.form:
                p_id = request.form.get('id')
                new_p = request.form.get('new_price')
                if new_p:
                    supabase.table("products").update({"price": new_p}).eq("id", p_id).execute()
            
            elif 'status_up' in request.form:
                order_id = request.form.get('oid')
                new_status = request.form.get('status_up')
                supabase.table("orders").update({"status": new_status}).eq("id", order_id).execute()
            
            return redirect('/admin')

        prods = supabase.table("products").select("*").execute().data
        orders = supabase.table("orders").select("*").order("id", desc=True).execute().data
        
        for o in orders:
            try:
                ids = eval(o['items'])
                items_names = supabase.table("products").select("name").in_("id", ids).execute().data
                o['items_list'] = ", ".join([i['name'] for i in items_names])
            except:
                o['items_list'] = "خطأ في جلب بيانات المنتجات"

        return render_template_string(STYLE + """
        <div style="padding:20px;">
            <h1 style="text-align:center;">لوحة التحكم</h1>
            <div style="display:grid; grid-template-columns: 1fr 1.5fr; gap:20px;">
                <div>
                    <div class="admin-card">
                        <h3>➕ إضافة منتج</h3>
                        <form method="POST">
                            <input name="n" placeholder="الاسم" required>
                            <input name="p" placeholder="السعر" required>
                            <input name="img" placeholder="رابط الصورة" required>
                            <button type="submit" name="add_p" class="btn-main">إضافة</button>
                        </form>
                    </div>
                    <div class="admin-card">
                        <h3>📦 قائمة المنتجات</h3>
                        {% for p in prods %}
                        <div style="border-bottom:1px solid #eee; padding:10px 0;">
                            <b>{{ p.name }}</b> ({{ p.price }} د.ل)
                            <form method="POST" style="margin-top:5px;">
                                <input type="hidden" name="id" value="{{ p.id }}">
                                <input name="new_price" placeholder="سعر جديد" style="width:80px; display:inline;">
                                <button type="submit" name="edit_p" class="btn-edit">تعديل</button>
                                <button type="submit" name="del_p" class="btn-del" onclick="return confirm('حذف؟')">🗑️</button>
                            </form>
                        </div>
                        {% endfor %}
                    </div>
                </div>
                <div>
                    <h3>🛒 الطلبات الواردة</h3>
                    {% for o in orders %}
                    <div class="admin-card">
                        <b>👤 الزبون:</b> {{ o.customer_name }} | <b>📞 الهاتف:</b> {{ o.phone }}<br>
                        <b>🛍️ المنتجات:</b> {{ o.items_list }}<br>
                        <b>الحالة:</b> <span style="color:var(--primary); font-weight:bold;">{{ o.status }}</span>
                        <form method="POST" style="margin-top:10px;">
                            <input type="hidden" name="oid" value="{{ o.id }}">
                            <button type="submit" name="status_up" value="Out for Delivery" class="btn-main" style="width:auto; background:orange;">🚚 توصيل</button>
                            <button type="submit" name="status_up" value="Completed" class="btn-main" style="width:auto; background:green;">✅ تم</button>
                        </form>
                    </div>
                    {% endfor %}
                </div>
            </div>
            <div style="text-align:center;"><a href="/logout" style="color:red;">خروج</a></div>
        </div>
        """, prods=prods, orders=orders)
    
    except Exception as e:
        return f"حدث خطأ: {str(e)}"

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)    