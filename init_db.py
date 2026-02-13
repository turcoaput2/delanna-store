import sqlite3

conn = sqlite3.connect("tienda.db")
conn.execute("""
CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT,
    precio REAL,
    imagen TEXT
)
""")
conn.commit()
conn.close()

print("Base creada")

