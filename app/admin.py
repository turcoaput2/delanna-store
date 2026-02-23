from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from . import db
from .extensions import admin_required
from .models import Order, Product, User

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if user is None or not user.is_admin or not check_password_hash(user.password_hash, password):
            flash("Acceso admin inválido.", "danger")
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
    image_url = request.form.get("image_url", "").strip()
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

    db.session.add(
        Product(
            name=name,
            description=description or None,
            image_url=image_url or None,
            price=price,
            stock=stock,
        )
    )
    db.session.commit()
    flash("Producto creado.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.post("/products/<int:product_id>/delete")
@admin_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
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
