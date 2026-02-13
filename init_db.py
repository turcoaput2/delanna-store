import os
import sqlite3

base_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(base_dir, "tienda.db")

conn = sqlite3.connect(db_path)
conn.execute(
    """
    CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        precio REAL NOT NULL,
        imagen TEXT NOT NULL
    )
    """
)
conn.commit()
conn.close()

print(f"Base creada en {db_path}")
