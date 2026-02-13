from functools import wraps
import os
import sqlite3
from datetime import datetime

from flask import Flask, flash, g, redirect, render_template, request, session, url_for, abort
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "delanna_secret")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "tienda.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "img")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


ORDER_STATUS = ["pendiente", "pagado", "enviado"]


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_error):
    db = g.pop("db", None)
    if db:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute("PRAGMA foreign_keys = ON")

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """
    )

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            precio REAL NOT NULL,
            imagen TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS cart_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            UNIQUE(user_id, product_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(product_id) REFERENCES productos(id) ON DELETE CASCADE
        )
        """
    )

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            total REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'pendiente',
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE RESTRICT
        )
        """
    )

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE,
            FOREIGN KEY(product_id) REFERENCES productos(id) ON DELETE RESTRICT
        )
        """
    )

    admin_email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    admin_password = os.environ.get("ADMIN_PASSWORD", "").strip()
    if admin_email and len(admin_password) >= 8:
        exists_admin = db.execute("SELECT id FROM users WHERE email = ?", (admin_email,)).fetchone()
        if not exists_admin:
            db.execute(
                "INSERT INTO users (email, password_hash, is_admin, created_at) VALUES (?, ?, 1, ?)",
                (admin_email, generate_password_hash(admin_password), datetime.utcnow().isoformat()),
            )

    cols = [row[1] for row in db.execute("PRAGMA table_info(productos)").fetchall()]
    if "created_at" not in cols:
        db.execute("ALTER TABLE productos ADD COLUMN created_at TEXT")
        db.execute(
            "UPDATE productos SET created_at = ? WHERE created_at IS NULL",
            (datetime.utcnow().isoformat(),),
        )

    db.commit()
    db.close()


init_db()


def now_iso():
    return datetime.utcnow().isoformat()


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return get_db().execute(
        "SELECT id, email, is_admin FROM users WHERE id = ?", (uid,)
    ).fetchone()


@app.context_processor
def inject_user_context():
    return {"current_user": current_user()}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Iniciá sesión para continuar.", "warning")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            return redirect(url_for("admin_login", next=request.path))
        if not user["is_admin"]:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


@app.errorhandler(403)
def forbidden(_error):
    return render_template("403.html"), 403


@app.route("/")
def index():
    productos = get_db().execute("SELECT * FROM productos ORDER BY id DESC").fetchall()
    return render_template("index.html", productos=productos)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not email or "@" not in email:
            flash("Ingresá un email válido.", "warning")
            return redirect(url_for("register"))
        if len(password) < 8:
            flash("La contraseña debe tener al menos 8 caracteres.", "warning")
            return redirect(url_for("register"))
        if password != confirm:
            flash("Las contraseñas no coinciden.", "warning")
            return redirect(url_for("register"))

        db = get_db()
        existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            flash("Ese email ya está registrado.", "warning")
            return redirect(url_for("register"))

        db.execute(
            "INSERT INTO users (email, password_hash, is_admin, created_at) VALUES (?, ?, 0, ?)",
            (email, generate_password_hash(password), now_iso()),
        )
        db.commit()
        flash("Cuenta creada correctamente. Ya podés iniciar sesión.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if not user or not check_password_hash(user["password_hash"], password):
            flash("Credenciales inválidas.", "danger")
            return redirect(url_for("login"))

        session.clear()
        session["user_id"] = user["id"]
        session["is_admin"] = bool(user["is_admin"])
        flash("Sesión iniciada.", "success")
        next_url = request.args.get("next")
        return redirect(next_url or url_for("index"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("index"))


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if not user or not user["is_admin"] or not check_password_hash(user["password_hash"], password):
            flash("Acceso admin inválido.", "danger")
            return redirect(url_for("admin_login"))

        session.clear()
        session["user_id"] = user["id"]
        session["is_admin"] = True
        return redirect(url_for("admin_dashboard"))

    return render_template("admin_login.html")


@app.route("/admin")
@admin_required
def admin_dashboard():
    db = get_db()
    productos = db.execute("SELECT * FROM productos ORDER BY id DESC").fetchall()
    orders = db.execute(
        """
        SELECT o.*, u.email
        FROM orders o
        JOIN users u ON o.user_id = u.id
        ORDER BY o.id DESC
        """
    ).fetchall()
    return render_template("admin.html", productos=productos, orders=orders, order_status=ORDER_STATUS)


@app.route("/admin/product/create", methods=["POST"])
@admin_required
def admin_create_product():
    nombre = request.form.get("nombre", "").strip()
    precio_raw = request.form.get("precio", "").strip()
    imagen = request.files.get("imagen")

    if not nombre or not precio_raw:
        flash("Nombre y precio son obligatorios.", "warning")
        return redirect(url_for("admin_dashboard"))

    try:
        precio = float(precio_raw)
        if precio <= 0:
            raise ValueError
    except ValueError:
        flash("El precio debe ser numérico y positivo.", "warning")
        return redirect(url_for("admin_dashboard"))

    if not imagen or not imagen.filename:
        flash("Subí una imagen para el producto.", "warning")
        return redirect(url_for("admin_dashboard"))

    filename = f"{int(datetime.utcnow().timestamp())}_{secure_filename(imagen.filename)}"
    imagen.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

    db = get_db()
    db.execute(
        "INSERT INTO productos (nombre, precio, imagen, created_at) VALUES (?, ?, ?, ?)",
        (nombre, precio, filename, now_iso()),
    )
    db.commit()
    flash("Producto creado.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/product/<int:product_id>/update", methods=["POST"])
@admin_required
def admin_update_product(product_id):
    nombre = request.form.get("nombre", "").strip()
    precio_raw = request.form.get("precio", "").strip()
    if not nombre or not precio_raw:
        flash("Nombre y precio son obligatorios.", "warning")
        return redirect(url_for("admin_dashboard"))

    try:
        precio = float(precio_raw)
        if precio <= 0:
            raise ValueError
    except ValueError:
        flash("Precio inválido.", "warning")
        return redirect(url_for("admin_dashboard"))

    db = get_db()
    db.execute(
        "UPDATE productos SET nombre = ?, precio = ? WHERE id = ?",
        (nombre, precio, product_id),
    )
    db.commit()
    flash("Producto actualizado.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/product/<int:product_id>/delete", methods=["POST"])
@admin_required
def admin_delete_product(product_id):
    db = get_db()
    db.execute("DELETE FROM productos WHERE id = ?", (product_id,))
    db.commit()
    flash("Producto eliminado.", "info")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/order/<int:order_id>/status", methods=["POST"])
@admin_required
def admin_update_order_status(order_id):
    status = request.form.get("status", "").strip().lower()
    if status not in ORDER_STATUS:
        flash("Estado inválido.", "warning")
        return redirect(url_for("admin_dashboard"))

    db = get_db()
    db.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    db.commit()
    flash("Estado del pedido actualizado.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/cart")
@login_required
def cart():
    rows = get_db().execute(
        """
        SELECT ci.product_id AS id, p.nombre, p.precio, p.imagen, ci.quantity
        FROM cart_items ci
        JOIN productos p ON p.id = ci.product_id
        WHERE ci.user_id = ?
        ORDER BY ci.id DESC
        """,
        (session["user_id"],),
    ).fetchall()

    items = []
    total = 0
    for row in rows:
        subtotal = row["precio"] * row["quantity"]
        total += subtotal
        items.append({**dict(row), "subtotal": subtotal})

    return render_template("carrito.html", productos=items, total=total)


@app.route("/cart/add/<int:product_id>", methods=["POST"])
@login_required
def add_to_cart(product_id):
    db = get_db()
    exists = db.execute("SELECT id FROM productos WHERE id = ?", (product_id,)).fetchone()
    if not exists:
        abort(404)

    db.execute(
        """
        INSERT INTO cart_items (user_id, product_id, quantity, created_at)
        VALUES (?, ?, 1, ?)
        ON CONFLICT(user_id, product_id)
        DO UPDATE SET quantity = quantity + 1
        """,
        (session["user_id"], product_id, now_iso()),
    )
    db.commit()
    flash("Producto agregado al carrito.", "success")
    return redirect(url_for("index"))


@app.route("/cart/update/<int:product_id>", methods=["POST"])
@login_required
def update_cart(product_id):
    qty_raw = request.form.get("quantity", "1")
    try:
        quantity = int(qty_raw)
    except ValueError:
        flash("Cantidad inválida.", "warning")
        return redirect(url_for("cart"))

    db = get_db()
    if quantity <= 0:
        db.execute(
            "DELETE FROM cart_items WHERE user_id = ? AND product_id = ?",
            (session["user_id"], product_id),
        )
    else:
        db.execute(
            "UPDATE cart_items SET quantity = ? WHERE user_id = ? AND product_id = ?",
            (quantity, session["user_id"], product_id),
        )
    db.commit()
    flash("Carrito actualizado.", "info")
    return redirect(url_for("cart"))


@app.route("/cart/remove/<int:product_id>", methods=["POST"])
@login_required
def remove_cart_item(product_id):
    db = get_db()
    db.execute(
        "DELETE FROM cart_items WHERE user_id = ? AND product_id = ?",
        (session["user_id"], product_id),
    )
    db.commit()
    flash("Producto eliminado del carrito.", "info")
    return redirect(url_for("cart"))


@app.route("/cart/clear", methods=["POST"])
@login_required
def clear_cart():
    db = get_db()
    db.execute("DELETE FROM cart_items WHERE user_id = ?", (session["user_id"],))
    db.commit()
    flash("Carrito vaciado.", "info")
    return redirect(url_for("cart"))


@app.route("/checkout", methods=["POST"])
@login_required
def checkout():
    db = get_db()
    cart_rows = db.execute(
        """
        SELECT ci.product_id, ci.quantity, p.precio
        FROM cart_items ci
        JOIN productos p ON p.id = ci.product_id
        WHERE ci.user_id = ?
        """,
        (session["user_id"],),
    ).fetchall()

    if not cart_rows:
        flash("No hay productos en el carrito.", "warning")
        return redirect(url_for("cart"))

    total = sum(row["quantity"] * row["precio"] for row in cart_rows)

    cursor = db.execute(
        "INSERT INTO orders (user_id, total, status, created_at) VALUES (?, ?, 'pendiente', ?)",
        (session["user_id"], total, now_iso()),
    )
    order_id = cursor.lastrowid

    for row in cart_rows:
        db.execute(
            "INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (?, ?, ?, ?)",
            (order_id, row["product_id"], row["quantity"], row["precio"]),
        )

    db.execute("DELETE FROM cart_items WHERE user_id = ?", (session["user_id"],))
    db.commit()

    return redirect(url_for("order_confirmation", order_id=order_id))


@app.route("/orders")
@login_required
def orders():
    rows = get_db().execute(
        "SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC", (session["user_id"],)
    ).fetchall()
    return render_template("orders.html", orders=rows)


@app.route("/order/<int:order_id>/confirmation")
@login_required
def order_confirmation(order_id):
    db = get_db()
    order = db.execute(
        "SELECT * FROM orders WHERE id = ? AND user_id = ?",
        (order_id, session["user_id"]),
    ).fetchone()
    if not order:
        abort(404)

    items = db.execute(
        """
        SELECT oi.quantity, oi.price, p.nombre
        FROM order_items oi
        JOIN productos p ON p.id = oi.product_id
        WHERE oi.order_id = ?
        """,
        (order_id,),
    ).fetchall()
    return render_template("order_confirmation.html", order=order, items=items)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
