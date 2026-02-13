from flask import Flask, render_template, request, redirect, session
import sqlite3, os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "delanna_secret"

UPLOAD_FOLDER = "static/img"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def get_db():
    conn = sqlite3.connect("tienda.db")
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def index():
    db = get_db()
    productos = db.execute("SELECT * FROM productos").fetchall()
    db.close()
    return render_template("index.html", productos=productos)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["user"] == "admin" and request.form["password"] == "1234":
            session["admin"] = True
            return redirect("/gestion-delanna")
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
        nombre = request.form["nombre"]
        precio = request.form["precio"]
        imagen = request.files["imagen"]

        filename = secure_filename(imagen.filename)
        imagen.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        db.execute(
            "INSERT INTO productos (nombre, precio, imagen) VALUES (?, ?, ?)",
            (nombre, precio, filename)
        )
        db.commit()

    productos = db.execute("SELECT * FROM productos").fetchall()
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
    return redirect("/gestion-delanna")

@app.route("/agregar/<int:id>")
def agregar(id):
    carrito = session.get("carrito", {})
    carrito[str(id)] = carrito.get(str(id), 0) + 1
    session["carrito"] = carrito
    return redirect("/")

@app.route("/carrito")
def carrito():
    db = get_db()
    carrito = session.get("carrito", {})
    productos = []
    total = 0

    for id, cantidad in carrito.items():
        p = db.execute("SELECT * FROM productos WHERE id = ?", (id,)).fetchone()
        if p:
            subtotal = p["precio"] * cantidad
            total += subtotal
            productos.append({
                "nombre": p["nombre"],
                "precio": p["precio"],
                "cantidad": cantidad,
                "subtotal": subtotal
            })

    db.close()
    return render_template("carrito.html", productos=productos, total=total)
