from flask import Blueprint, g, render_template

from .extensions import login_required
from .models import Order

orders_bp = Blueprint("orders", __name__, url_prefix="/orders")


@orders_bp.get("/")
@login_required
def my_orders():
    orders = Order.query.filter_by(user_id=g.user.id).order_by(Order.created_at.desc()).all()
    return render_template("orders/list.html", orders=orders)


@orders_bp.get("/<int:order_id>/confirmacion")
@login_required
def order_confirmation(order_id):
    order = (
        Order.query.filter_by(id=order_id, user_id=g.user.id)
        .order_by(Order.created_at.desc())
        .first_or_404()
    )
    return render_template("orders/confirmation.html", order=order)
