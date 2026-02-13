from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    precio = db.Column(db.Integer, nullable=False)
    imagen = db.Column(db.String(200))
    descripcion = db.Column(db.Text)
