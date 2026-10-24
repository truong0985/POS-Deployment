import os, logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from flask import Flask, request, redirect, url_for, render_template_string, flash, Response
import mysql.connector
from mysql.connector import pooling
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "development-only-change-me")
os.makedirs("/var/log/pos", exist_ok=True)
handler = RotatingFileHandler("/var/log/pos/app.log", maxBytes=2_000_000, backupCount=3)
handler.setFormatter(logging.Formatter('{"time":"%(asctime)s","level":"%(levelname)s","message":"%(message)s"}'))
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

REQUESTS = Counter("pos_http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])
LATENCY = Histogram("pos_http_request_duration_seconds", "HTTP request duration", ["endpoint"])
db_pool = None

def get_pool():
    global db_pool
    if db_pool is None:
        db_pool = pooling.MySQLConnectionPool(
            pool_name="pos_pool", pool_size=5,
            host=os.getenv("DB_HOST", "mysql_db"),
            port=int(os.getenv("DB_PORT", "3306")),
            database=os.getenv("DB_NAME", "pos_db"),
            user=os.getenv("DB_USER", "pos_user"),
            password=os.getenv("DB_PASSWORD", "")
        )
    return db_pool

def query(sql, params=(), fetch=False):
    conn = get_pool().get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        result = cur.fetchall() if fetch else cur.lastrowid
        if not fetch:
            conn.commit()
        cur.close()
        return result
    finally:
        conn.close()

@app.before_request
def before_request():
    request._started_at = datetime.now().timestamp()

@app.after_request
def after_request(response):
    endpoint = request.endpoint or "unknown"
    elapsed = max(0, datetime.now().timestamp() - getattr(request, "_started_at", datetime.now().timestamp()))
    REQUESTS.labels(request.method, endpoint, str(response.status_code)).inc()
    LATENCY.labels(endpoint).observe(elapsed)
    return response

BASE = """
<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>POS - Quản lý cửa hàng</title>
<style>
body{font-family:Arial,sans-serif;background:#f3f6fa;color:#172033;margin:0}header{background:#16324f;color:white;padding:22px 5%}
main{max-width:1100px;margin:25px auto;padding:0 18px}.cards{display:flex;gap:14px;flex-wrap:wrap}.card{background:white;padding:18px;border-radius:12px;box-shadow:0 2px 8px #0001;flex:1;min-width:180px}
table{width:100%;border-collapse:collapse;background:white;margin-top:14px}th,td{padding:11px;border-bottom:1px solid #e5e7eb;text-align:left}th{background:#e8eef5}
input,select,button{padding:10px;margin:4px 3px;border:1px solid #cbd5e1;border-radius:6px}button{background:#176b87;color:white;border:0;cursor:pointer}.msg{padding:10px;background:#fff2c6;border-radius:8px}
a{color:#176b87}form.inline{display:inline}
</style></head><body><header><h1>Hệ thống Quản lý Cửa hàng / POS</h1><p>Quản lý sản phẩm, tồn kho và hóa đơn bán hàng</p></header><main>
{% with messages = get_flashed_messages() %}{% if messages %}{% for m in messages %}<p class="msg">{{m}}</p>{% endfor %}{% endif %}{% endwith %}
{{ body|safe }}
</main></body></html>
"""

@app.route("/")
def index():
    products = query("SELECT id,name,sku,price,stock FROM products ORDER BY id DESC", fetch=True)
    sales = query("SELECT COUNT(*) AS n, COALESCE(SUM(total),0) AS total FROM sales", fetch=True)[0]
    today = query("SELECT COALESCE(SUM(total),0) AS total FROM sales WHERE DATE(created_at)=CURDATE()", fetch=True)[0]
    body = render_template_string("""
    <div class="cards"><div class="card"><h3>Sản phẩm</h3><h2>{{products|length}}</h2></div>
    <div class="card"><h3>Tổng hóa đơn</h3><h2>{{sales.n}}</h2></div><div class="card"><h3>Doanh thu toàn thời gian</h3><h2>{{'%.0f'|format(sales.total)}} đ</h2></div>
    <div class="card"><h3>Doanh thu hôm nay</h3><h2>{{'%.0f'|format(today.total)}} đ</h2></div></div>
    <h2>Thêm sản phẩm</h2><form method="post" action="/products">
    <input name="name" placeholder="Tên sản phẩm" required><input name="sku" placeholder="Mã SKU" required>
    <input name="price" type="number" min="0" step="100" placeholder="Giá bán (đ)" required>
    <input name="stock" type="number" min="0" placeholder="Tồn kho" required><button>Thêm sản phẩm</button></form>
    <h2>Danh sách sản phẩm</h2><table><tr><th>ID</th><th>Tên</th><th>SKU</th><th>Giá</th><th>Tồn</th><th>Bán</th></tr>
    {% for p in products %}<tr><td>{{p.id}}</td><td>{{p.name}}</td><td>{{p.sku}}</td><td>{{'%.0f'|format(p.price)}} đ</td><td>{{p.stock}}</td><td>
    <form class="inline" method="post" action="/sales"><input type="hidden" name="product_id" value="{{p.id}}">
    <input name="quantity" type="number" min="1" max="{{p.stock}}" value="1" style="width:65px" {% if p.stock < 1 %}disabled{% endif %}>
    <button {% if p.stock < 1 %}disabled{% endif %}>Tạo hóa đơn</button></form></td></tr>{% endfor %}</table>
    <p><a href="/sales">Xem hóa đơn bán hàng</a> · <a href="/health">Health check</a> · <a href="/metrics">Metrics</a></p>
    """, products=products, sales=sales, today=today)
    return render_template_string(BASE, body=body)

@app.post("/products")
def add_product():
    name, sku = request.form.get("name","").strip(), request.form.get("sku","").strip()
    try:
        price, stock = float(request.form.get("price", "0")), int(request.form.get("stock", "0"))
        if not name or not sku or price < 0 or stock < 0: raise ValueError()
        query("INSERT INTO products(name,sku,price,stock) VALUES(%s,%s,%s,%s)", (name,sku,price,stock))
        app.logger.info("product_created sku=%s", sku)
        flash("Đã thêm sản phẩm.")
    except mysql.connector.IntegrityError:
        flash("Mã SKU đã tồn tại.")
    except (ValueError, TypeError):
        flash("Dữ liệu sản phẩm không hợp lệ.")
    except Exception:
        app.logger.exception("add_product_failed")
        flash("Không thể thêm sản phẩm. Hãy kiểm tra log.")
    return redirect(url_for("index"))

@app.post("/sales")
def create_sale():
    try:
        product_id, quantity = int(request.form["product_id"]), int(request.form["quantity"])
        if quantity < 1: raise ValueError()
        conn = get_pool().get_connection()
        try:
            conn.start_transaction()
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT id,name,price,stock FROM products WHERE id=%s FOR UPDATE", (product_id,))
            product = cur.fetchone()
            if not product or product["stock"] < quantity:
                conn.rollback()
                flash("Sản phẩm không tồn tại hoặc không đủ tồn kho.")
            else:
                total = float(product["price"]) * quantity
                cur.execute("INSERT INTO sales(product_id,product_name,quantity,unit_price,total) VALUES(%s,%s,%s,%s,%s)",
                            (product["id"], product["name"], quantity, product["price"], total))
                cur.execute("UPDATE products SET stock=stock-%s WHERE id=%s", (quantity, product_id))
                conn.commit()
                app.logger.info("sale_created product_id=%s quantity=%s total=%.2f", product_id, quantity, total)
                flash("Tạo hóa đơn thành công. Tổng tiền: {:,.0f} đ".format(total))
            cur.close()
        finally:
            conn.close()
    except (ValueError, KeyError):
        flash("Số lượng không hợp lệ.")
    except Exception:
        app.logger.exception("create_sale_failed")
        flash("Không thể tạo hóa đơn. Hãy kiểm tra log.")
    return redirect(url_for("index"))

@app.route("/sales")
def sales_list():
    sales = query("SELECT id,product_name,quantity,unit_price,total,created_at FROM sales ORDER BY id DESC LIMIT 100", fetch=True)
    body = render_template_string("""<h2>Hóa đơn bán hàng gần đây</h2><table><tr><th>Mã HĐ</th><th>Sản phẩm</th><th>Số lượng</th><th>Đơn giá</th><th>Thành tiền</th><th>Thời gian</th></tr>
    {% for s in sales %}<tr><td>{{s.id}}</td><td>{{s.product_name}}</td><td>{{s.quantity}}</td><td>{{'%.0f'|format(s.unit_price)}} đ</td><td>{{'%.0f'|format(s.total)}} đ</td><td>{{s.created_at}}</td></tr>{% endfor %}</table><p><a href="/">← Quay lại</a></p>""", sales=sales)
    return render_template_string(BASE, body=body)

@app.route("/health")
def health():
    try:
        query("SELECT 1", fetch=True)
        return {"status":"ok","database":"connected"}, 200
    except Exception as exc:
        app.logger.exception("health_check_failed")
        return {"status":"error","database":"unavailable"}, 503

@app.route("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
