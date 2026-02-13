import os
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash

base_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(base_dir, "tienda.db")

conn = sqlite3.connect(db_path)
conn.execute("PRAGMA foreign_keys = ON")

conn.execute(
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        is_admin INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    )
    """
)

conn.execute(
    """
    CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        precio REAL NOT NULL,
        imagen TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """
)

conn.execute(
    """
    CREATE TABLE IF NOT EXISTS cart_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        UNIQUE(user_id, product_id),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(product_id) REFERENCES productos(id) ON DELETE CASCADE
    )
    """
)

conn.execute(
    """
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        total REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'pendiente',
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE RESTRICT
    )
    """
)

conn.execute(
    """
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        price REAL NOT NULL,
        FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE,
        FOREIGN KEY(product_id) REFERENCES productos(id) ON DELETE RESTRICT
    )
    """
)

admin_email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
admin_password = os.environ.get("ADMIN_PASSWORD", "").strip()
if admin_email and len(admin_password) >= 8:
    found = conn.execute("SELECT id FROM users WHERE email = ?", (admin_email,)).fetchone()
    if not found:
        conn.execute(
            "INSERT INTO users (email, password_hash, is_admin, created_at) VALUES (?, ?, 1, ?)",
            (admin_email, generate_password_hash(admin_password), datetime.utcnow().isoformat()),
        )

conn.commit()
conn.close()

print(f"Base inicializada en {db_path}")
