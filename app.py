from flask import Flask, render_template, request, redirect, session, url_for, flash
import os
import sqlite3
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "delanna_secret")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "tienda.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "img")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            precio REAL NOT NULL,
            imagen TEXT NOT NULL
        )
        """
    )
    db.commit()
    db.close()


init_db()


@app.route("/")
def index():
    db = get_db()
    productos = db.execute("SELECT * FROM productos ORDER BY id DESC").fetchall()
    db.close()
    return render_template("index.html", productos=productos)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["user"] == "admin" and request.form["password"] == "1234":
            session["admin"] = True
            return redirect("/gestion-delanna")
        flash("Credenciales inválidas", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/gestion-delanna", methods=["GET", "POST"])
def admin():
    if not session.get("admin"):
        return redirect("/login")

    db = get_db()

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        precio_raw = request.form.get("precio", "").strip()
        imagen = request.files.get("imagen")

        if not nombre or not precio_raw:
            flash("Nombre y precio son obligatorios.", "warning")
            return redirect("/gestion-delanna")

        try:
            precio = float(precio_raw)
            if precio <= 0:
                raise ValueError
        except ValueError:
            flash("El precio debe ser un número positivo.", "warning")
            return redirect("/gestion-delanna")

        if not imagen or not imagen.filename:
            flash("Debes seleccionar una imagen.", "warning")
            return redirect("/gestion-delanna")

        filename = secure_filename(imagen.filename)
        image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        imagen.save(image_path)

        db.execute(
            "INSERT INTO productos (nombre, precio, imagen) VALUES (?, ?, ?)",
            (nombre, precio, filename),
        )
        db.commit()
        flash("Producto agregado correctamente.", "success")

    productos = db.execute("SELECT * FROM productos ORDER BY id DESC").fetchall()
    db.close()
    return render_template("admin.html", productos=productos)


@app.route("/eliminar/<int:id>")
def eliminar(id):
    if not session.get("admin"):
        return redirect("/login")

    db = get_db()
    db.execute("DELETE FROM productos WHERE id = ?", (id,))
    db.commit()
    db.close()
    flash("Producto eliminado.", "info")
    return redirect("/gestion-delanna")


@app.route("/agregar/<int:id>")
def agregar(id):
    carrito = session.get("carrito", {})
    carrito[str(id)] = carrito.get(str(id), 0) + 1
    session["carrito"] = carrito
    flash("Producto agregado al carrito.", "success")
    return redirect("/")


@app.route("/quitar/<int:id>")
def quitar(id):
    carrito = session.get("carrito", {})
    item_id = str(id)

    if item_id in carrito:
        carrito[item_id] -= 1
        if carrito[item_id] <= 0:
            del carrito[item_id]

    session["carrito"] = carrito
    return redirect(url_for("carrito"))


@app.route("/vaciar-carrito")
def vaciar_carrito():
    session["carrito"] = {}
    return redirect(url_for("carrito"))


@app.route("/carrito")
def carrito():
    db = get_db()
    carrito_sesion = session.get("carrito", {})
    productos = []
    total = 0

    for id_producto, cantidad in carrito_sesion.items():
        p = db.execute("SELECT * FROM productos WHERE id = ?", (id_producto,)).fetchone()
        if p:
            subtotal = p["precio"] * cantidad
            total += subtotal
            productos.append(
                {
                    "id": p["id"],
                    "nombre": p["nombre"],
                    "precio": p["precio"],
                    "cantidad": cantidad,
                    "subtotal": subtotal,
                }
            )

    db.close()
    return render_template("carrito.html", productos=productos, total=total)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
