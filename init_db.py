from app import create_app, db
from app.models import Product, User
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    db.create_all()

    if not User.query.filter_by(email="admin@delanna.com").first():
        db.session.add(
            User(
                email="admin@delanna.com",
                password_hash=generate_password_hash("admin1234"),
                is_admin=True,
            )
        )

    if Product.query.count() == 0:
        db.session.add_all(
            [
                Product(
                    name="Conjunto Encaje Rosa",
                    description="Conjunto premium de encaje suave.",
                    image_url="https://images.unsplash.com/photo-1591369822096-ffd140ec948f?auto=format&fit=crop&w=900&q=80",
                    price=25999,
                    stock=12,
                ),
                Product(
                    name="Body Negro Clásico",
                    description="Body elegante y cómodo para uso diario.",
                    image_url="https://images.unsplash.com/photo-1617727553252-65863c156eb0?auto=format&fit=crop&w=900&q=80",
                    price=19999,
                    stock=20,
                ),
            ]
        )

    db.session.commit()
    print("Base inicializada con usuario admin y productos demo.")
