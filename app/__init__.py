from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    
    # Configuración de BD
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///delanna.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-prod')
    
    # Inicializar BD
    db.init_app(app)
    
    # Registrar blueprints
    from app.auth import auth_bp
    from app.shop import shop_bp
    from app.admin import admin_bp
    from app.orders import orders_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(shop_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(orders_bp)
    
    # Crear tablas
    with app.app_context():
        db.create_all()
    
    return app