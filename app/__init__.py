import os

from dotenv import load_dotenv
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy

load_dotenv()


db = SQLAlchemy()

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", "sqlite:///delanna.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-prod")
    app.config["ADMIN_URL_PREFIX"] = os.environ.get("ADMIN_URL_PREFIX", "/atelier-privado-delanna")
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB
    app.config["MP_ACCESS_TOKEN"] = os.environ.get("MP_ACCESS_TOKEN", "")
    app.config["BASE_URL"] = os.environ.get("BASE_URL", "")

    upload_path = os.path.join(app.static_folder, "uploads")
    os.makedirs(upload_path, exist_ok=True)
    app.config["UPLOAD_FOLDER"] = upload_path

    db.init_app(app)

    from . import models  # noqa: F401
    from .admin import admin_bp
    from .auth import auth_bp
    from .orders import orders_bp
    from .payments import payments_bp
    from .shop import shop_bp
    from .extensions import load_logged_in_user

    app.before_request(load_logged_in_user)

    app.register_blueprint(auth_bp)
    app.register_blueprint(shop_bp)
    app.register_blueprint(admin_bp, url_prefix=app.config["ADMIN_URL_PREFIX"])
    app.register_blueprint(orders_bp)
    app.register_blueprint(payments_bp)

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
        _seed_admin(app)

    return app


def _seed_admin(app):
    """Create the admin user if it doesn't exist yet."""
    from werkzeug.security import generate_password_hash
    from .models import User

    email = os.environ.get("ADMIN_EMAIL", "aputbenjamin@gmail.com")
    password = os.environ.get("ADMIN_PASSWORD", "123456")

    if not User.query.filter_by(email=email).first():
        db.session.add(User(
            email=email,
            password_hash=generate_password_hash(password),
            is_admin=True,
        ))
        db.session.commit()
        app.logger.info("Admin user created: %s", email)
