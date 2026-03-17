import os
import uuid

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename

from . import db
from .extensions import admin_required
from .models import Order, Product, User

admin_bp = Blueprint("admin", __name__)


def _save_image(file):
    """Save uploaded image and return the static URL path."""
    from . import allowed_file

    if not file or file.filename == "":
        return None
    if not allowed_file(file.filename):
        return None

    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)
    return url_for("static", filename=f"uploads/{filename}")


@admin_bp.route("/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if user is None:
            flash("No se encontró el usuario.", "danger")
        elif not user.is_admin:
            flash("Este usuario no es administrador.", "danger")
        elif not check_password_hash(user.password_hash, password):
            flash("Contraseña incorrecta.", "danger")
        else:
            session.clear()
            session["user_id"] = user.id
            flash("Accediste al panel de administración.", "success")
            return redirect(url_for("admin.dashboard"))

    return render_template("admin/login.html")


@admin_bp.get("/")
def admin_root():
    return redirect(url_for("admin.dashboard"))


@admin_bp.get("/dashboard")
@admin_required
def dashboard():
    products = Product.query.order_by(Product.created_at.desc()).all()
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template("admin/dashboard.html", products=products, orders=orders)


@admin_bp.post("/products")
@admin_required
def create_product():
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    price_raw = request.form.get("price", "0")
    stock_raw = request.form.get("stock", "0")

    try:
        price = float(price_raw)
        stock = int(stock_raw)
    except ValueError:
        flash("Precio y stock deben ser numéricos.", "danger")
        return redirect(url_for("admin.dashboard"))

    if not name or price < 0 or stock < 0:
        flash("Completá correctamente nombre, precio y stock.", "danger")
        return redirect(url_for("admin.dashboard"))

    image_url = None
    if "image" in request.files:
        image_url = _save_image(request.files["image"])

    db.session.add(
        Product(
            name=name,
            description=description or None,
            image_url=image_url,
            price=price,
            stock=stock,
        )
    )
    db.session.commit()
    flash("Producto creado.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        try:
            price = float(request.form.get("price", "0"))
            stock = int(request.form.get("stock", "0"))
        except ValueError:
            flash("Precio y stock deben ser numéricos.", "danger")
            return redirect(url_for("admin.edit_product", product_id=product_id))

        if not name or price < 0 or stock < 0:
            flash("Completá correctamente los campos.", "danger")
            return redirect(url_for("admin.edit_product", product_id=product_id))

        product.name = name
        product.description = description or None
        product.price = price
        product.stock = stock

        if "image" in request.files and request.files["image"].filename:
            new_url = _save_image(request.files["image"])
            if new_url:
                if product.image_url and "/uploads/" in product.image_url:
                    old_filename = product.image_url.rsplit("/", 1)[-1]
                    old_path = os.path.join(current_app.config["UPLOAD_FOLDER"], old_filename)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                product.image_url = new_url

        db.session.commit()
        flash("Producto actualizado.", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("admin/edit_product.html", product=product)


@admin_bp.post("/products/<int:product_id>/delete")
@admin_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    if product.image_url and "/uploads/" in product.image_url:
        filename = product.image_url.rsplit("/", 1)[-1]
        filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
        if os.path.exists(filepath):
            os.remove(filepath)
    db.session.delete(product)
    db.session.commit()
    flash("Producto eliminado.", "info")
    return redirect(url_for("admin.dashboard"))


@admin_bp.post("/orders/<int:order_id>/status")
@admin_required
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    status = request.form.get("status", "pendiente")
    allowed = {"pendiente", "pagado", "enviado"}
    if status not in allowed:
        abort(400)

    order.status = status
    db.session.commit()
    flash(f"Pedido #{order.id} actualizado a {status}.", "success")
    return redirect(url_for("admin.dashboard"))
