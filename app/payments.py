import os

import mercadopago
from flask import Blueprint, current_app, flash, g, jsonify, redirect, request, url_for

from . import db
from .extensions import login_required
from .models import CartItem, Order, OrderItem

payments_bp = Blueprint("payments", __name__, url_prefix="/payments")


def _get_mp_sdk():
    token = current_app.config.get("MP_ACCESS_TOKEN")
    if not token:
        return None
    return mercadopago.SDK(token)


@payments_bp.post("/create")
@login_required
def create_preference():
    """Create a MercadoPago checkout preference from the user's cart."""
    cart_items = CartItem.query.filter_by(user_id=g.user.id).all()
    if not cart_items:
        flash("Tu carrito está vacío.", "danger")
        return redirect(url_for("shop.cart"))

    sdk = _get_mp_sdk()
    if not sdk:
        flash("Pagos online no configurados. Usá transferencia.", "danger")
        return redirect(url_for("shop.cart"))

    # Build order first (status = pending payment)
    total = sum(item.quantity * item.product.price for item in cart_items)
    order = Order(user_id=g.user.id, total=total, status="pendiente")
    db.session.add(order)
    db.session.flush()

    # Check stock before creating order
    for item in cart_items:
        if item.quantity > item.product.stock:
            flash(f"{item.product.name} solo tiene {item.product.stock} en stock.", "danger")
            return redirect(url_for("shop.cart"))

    items_mp = []
    for item in cart_items:
        db.session.add(
            OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.product.price,
            )
        )
        item.product.stock -= item.quantity
        items_mp.append({
            "title": item.product.name,
            "quantity": item.quantity,
            "unit_price": float(item.product.price),
            "currency_id": "ARS",
        })
        db.session.delete(item)

    db.session.commit()

    base_url = current_app.config.get("BASE_URL", request.host_url.rstrip("/"))

    preference_data = {
        "items": items_mp,
        "external_reference": str(order.id),
        "back_urls": {
            "success": f"{base_url}/payments/success?order_id={order.id}",
            "failure": f"{base_url}/payments/failure?order_id={order.id}",
            "pending": f"{base_url}/payments/pending?order_id={order.id}",
        },
        "auto_return": "approved",
        "notification_url": f"{base_url}/payments/webhook",
    }

    result = sdk.preference().create(preference_data)
    pref = result.get("response", {})

    if "init_point" not in pref:
        flash("Error al crear el pago. Intentá de nuevo.", "danger")
        return redirect(url_for("shop.cart"))

    return redirect(pref["init_point"])


@payments_bp.get("/success")
@login_required
def payment_success():
    order_id = request.args.get("order_id")
    if order_id:
        order = Order.query.filter_by(id=order_id, user_id=g.user.id).first()
        if order and order.status == "pendiente":
            order.status = "pagado"
            db.session.commit()
    flash("¡Pago recibido! Gracias por tu compra.", "success")
    return redirect(url_for("orders.order_confirmation", order_id=order_id))


@payments_bp.get("/failure")
@login_required
def payment_failure():
    order_id = request.args.get("order_id")
    flash("El pago no se pudo completar. Podés reintentar o elegir otro método.", "danger")
    return redirect(url_for("orders.my_orders"))


@payments_bp.get("/pending")
@login_required
def payment_pending():
    order_id = request.args.get("order_id")
    flash("Tu pago está pendiente de confirmación.", "info")
    return redirect(url_for("orders.order_confirmation", order_id=order_id))


@payments_bp.post("/webhook")
def webhook():
    """MercadoPago IPN webhook — updates order status."""
    sdk = _get_mp_sdk()
    if not sdk:
        return jsonify(ok=False), 400

    data = request.json or {}
    if data.get("type") == "payment":
        payment_id = data.get("data", {}).get("id")
        if payment_id:
            payment_info = sdk.payment().get(payment_id)
            pay = payment_info.get("response", {})
            ext_ref = pay.get("external_reference")
            status = pay.get("status")

            if ext_ref:
                order = Order.query.get(int(ext_ref))
                if order:
                    if status == "approved":
                        order.status = "pagado"
                    elif status in ("pending", "in_process"):
                        order.status = "pendiente"
                    db.session.commit()

    return jsonify(ok=True), 200
