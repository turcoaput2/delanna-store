import os

from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", "sqlite:///delanna.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-prod")
    app.config["ADMIN_URL_PREFIX"] = os.environ.get("ADMIN_URL_PREFIX", "/atelier-privado-delanna")

    db.init_app(app)

    from . import models  # noqa: F401
    from .admin import admin_bp
    from .auth import auth_bp
    from .orders import orders_bp
    from .shop import shop_bp
    from .extensions import load_logged_in_user

    app.before_request(load_logged_in_user)

    app.register_blueprint(auth_bp)
    app.register_blueprint(shop_bp)
    app.register_blueprint(admin_bp, url_prefix=app.config["ADMIN_URL_PREFIX"])
    app.register_blueprint(orders_bp)

    @app.errorhandler(403)
    def forbidden(_):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(_):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(_):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    with app.app_context():
        db.create_all()

    return app
