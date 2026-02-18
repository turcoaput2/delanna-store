from functools import wraps

from flask import abort, g, redirect, request, session, url_for

from .models import User


def load_logged_in_user():
    user_id = session.get("user_id")
    g.user = User.query.get(user_id) if user_id else None


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped_view


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("admin.admin_login", next=request.path))
        if not g.user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped_view
