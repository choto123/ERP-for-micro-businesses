import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), "erp.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username   TEXT NOT NULL UNIQUE,
    nombre     TEXT NOT NULL,
    password   TEXT NOT NULL,
    rol        TEXT NOT NULL DEFAULT 'viewer',
    activo     INTEGER NOT NULL DEFAULT 1,
    creado_en  TEXT DEFAULT (date('now'))
);

CREATE TABLE IF NOT EXISTS clientes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre        TEXT NOT NULL,
    telefono      TEXT DEFAULT '',
    email         TEXT DEFAULT '',
    direccion     TEXT DEFAULT '',
    tipo          TEXT DEFAULT 'Regular',
    total_compras REAL DEFAULT 0,
    ultima_compra TEXT
);

CREATE TABLE IF NOT EXISTS proveedores (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa   TEXT NOT NULL,
    contacto  TEXT DEFAULT '',
    telefono  TEXT DEFAULT '',
    email     TEXT DEFAULT '',
    categoria TEXT DEFAULT '',
    estado    TEXT DEFAULT 'Activo'
);

CREATE TABLE IF NOT EXISTS productos (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre       TEXT NOT NULL,
    categoria    TEXT DEFAULT '',
    proveedor_id INTEGER REFERENCES proveedores(id),
    precio       REAL DEFAULT 0,
    costo        REAL DEFAULT 0,
    stock        INTEGER DEFAULT 0,
    stock_min    INTEGER DEFAULT 5,
    unidad       TEXT DEFAULT 'und'
);

CREATE TABLE IF NOT EXISTS ventas (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha      TEXT NOT NULL,
    cliente_id INTEGER REFERENCES clientes(id),
    total      REAL DEFAULT 0,
    pago       TEXT DEFAULT 'Efectivo',
    estado     TEXT DEFAULT 'Pagado'
);

CREATE TABLE IF NOT EXISTS venta_items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    venta_id     INTEGER NOT NULL REFERENCES ventas(id),
    producto_id  INTEGER REFERENCES productos(id),
    nombre       TEXT NOT NULL,
    cantidad     INTEGER DEFAULT 1,
    precio_unit  REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS gastos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    descripcion TEXT NOT NULL,
    categoria   TEXT DEFAULT 'Otros',
    monto       REAL DEFAULT 0,
    fecha       TEXT NOT NULL,
    notas       TEXT DEFAULT ''
);
"""

USUARIOS_SEED = [
    {"username": "juancho",     "nombre": "Juan David Orozco",    "password": "98564768",     "rol": "admin",  "activo": 1},
    {"username": "luxa",     "nombre": "Luz Albany Ramirez",    "password": "43365904",     "rol": "admin",  "activo": 1},
    {"username": "admin",     "nombre": "administrador",    "password": "admin123",     "rol": "admin",  "activo": 1},
    {"username": "vendedor",  "nombre": "Vendedor",         "password": "vendedor123",  "rol": "viewer", "activo": 1},
    {"username": "bloqueado", "nombre": "Usuario Bloqueado","password": "bloqueado123", "rol": "viewer", "activo": 0},
]

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    conn.executescript(SCHEMA)
    for u in USUARIOS_SEED:
        existe = conn.execute("SELECT id FROM usuarios WHERE username=?", (u["username"],)).fetchone()
        if not existe:
            conn.execute(
                "INSERT INTO usuarios (username, nombre, password, rol, activo) VALUES (?,?,?,?,?)",
                (u["username"], u["nombre"], generate_password_hash(u["password"]), u["rol"], u["activo"])
            )
    conn.commit()
    conn.close()
    print(f"[DB] Base de datos lista en {DB_PATH}")
