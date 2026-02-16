# backend/db.py
import sqlite3
import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DATA_DIR, "satisfactory.db")
NODES_PATH = os.path.join(DATA_DIR, "resource_nodes.json")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_resource_nodes(db: sqlite3.Connection):
    """Create and populate resource_nodes table from JSON if not exists."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS resource_nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            purity TEXT NOT NULL,
            x REAL NOT NULL,
            y REAL NOT NULL,
            z REAL NOT NULL
        )
    """)
    cursor = db.execute("SELECT COUNT(*) FROM resource_nodes")
    if cursor.fetchone()[0] > 0:
        return
    with open(NODES_PATH) as f:
        data = json.load(f)
    nodes = data.get("resource_nodes", data) if isinstance(data, dict) else data
    db.executemany(
        "INSERT INTO resource_nodes (type, purity, x, y, z) VALUES (?, ?, ?, ?, ?)",
        [(n["type"], n["purity"], n["x"], n["y"], n["z"]) for n in nodes],
    )
    db.commit()


def get_resource_nodes(db: sqlite3.Connection) -> list[dict]:
    rows = db.execute("SELECT type, purity, x, y, z FROM resource_nodes").fetchall()
    return [dict(r) for r in rows]
