from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from . import db
from .extensions import login_required
from .models import CartItem, Order, OrderItem, Product

shop_bp = Blueprint("shop", __name__)


@shop_bp.route("/")
def index():
    products = Product.query.order_by(Product.created_at.desc()).all()
    return render_template("shop/index.html", products=products)


@shop_bp.route("/carrito")
@login_required
def cart():
    cart_items = (
        CartItem.query.filter_by(user_id=g.user.id)
        .join(Product)
        .order_by(CartItem.created_at.desc())
        .all()
    )
    total = sum(item.quantity * item.product.price for item in cart_items)
    return render_template("shop/cart.html", cart_items=cart_items, total=total)


@shop_bp.post("/carrito/agregar/<int:product_id>")
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    quantity = max(1, int(request.form.get("quantity", 1)))

    existing = CartItem.query.filter_by(user_id=g.user.id, product_id=product.id).first()
    if existing:
        existing.quantity += quantity
    else:
        existing = CartItem(user_id=g.user.id, product_id=product.id, quantity=quantity)
        db.session.add(existing)

    db.session.commit()
    flash(f"{product.name} se agregó al carrito.", "success")
    return redirect(url_for("shop.index"))


@shop_bp.post("/carrito/actualizar/<int:item_id>")
@login_required
def update_cart_item(item_id):
    item = CartItem.query.filter_by(id=item_id, user_id=g.user.id).first_or_404()
    quantity = int(request.form.get("quantity", 1))

    if quantity <= 0:
        db.session.delete(item)
    else:
        item.quantity = quantity

    db.session.commit()
    flash("Carrito actualizado.", "info")
    return redirect(url_for("shop.cart"))


@shop_bp.post("/carrito/eliminar/<int:item_id>")
@login_required
def remove_cart_item(item_id):
    item = CartItem.query.filter_by(id=item_id, user_id=g.user.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash("Producto eliminado del carrito.", "info")
    return redirect(url_for("shop.cart"))


@shop_bp.post("/checkout")
@login_required
def checkout():
    cart_items = CartItem.query.filter_by(user_id=g.user.id).all()
    if not cart_items:
        flash("No podés confirmar un pedido con el carrito vacío.", "danger")
        return redirect(url_for("shop.cart"))

    total = sum(item.quantity * item.product.price for item in cart_items)
    order = Order(user_id=g.user.id, total=total, status="pendiente")
    db.session.add(order)
    db.session.flush()

    for item in cart_items:
        db.session.add(
            OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.product.price,
            )
        )
        db.session.delete(item)

    db.session.commit()
    flash(f"Pedido #{order.id} confirmado con éxito.", "success")
    return redirect(url_for("orders.order_confirmation", order_id=order.id))
