"""SQLite persistence helpers for the inventory API."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity >= 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""


def connect(database_path: str) -> sqlite3.Connection:
    """Open a configured connection that returns rows addressable by column name."""
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def initialise(database_path: str) -> None:
    """Create the database parent directory and schema when they do not exist."""
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    with closing(connect(database_path)) as connection:
        connection.execute(SCHEMA)
        connection.commit()


def list_items(database_path: str) -> list[dict[str, Any]]:
    """Return all inventory records in stable identifier order."""
    with closing(connect(database_path)) as connection:
        rows = connection.execute(
            "SELECT id, sku, name, quantity, created_at, updated_at FROM items ORDER BY id"
        ).fetchall()
    return [dict(row) for row in rows]


def get_item(database_path: str, item_id: int) -> dict[str, Any] | None:
    """Return one inventory record or None when its identifier is absent."""
    with closing(connect(database_path)) as connection:
        row = connection.execute(
            "SELECT id, sku, name, quantity, created_at, updated_at FROM items WHERE id = ?",
            (item_id,),
        ).fetchone()
    return dict(row) if row else None


def create_item(database_path: str, *, sku: str, name: str, quantity: int) -> dict[str, Any]:
    """Insert and return a new inventory record."""
    with closing(connect(database_path)) as connection:
        cursor = connection.execute(
            "INSERT INTO items (sku, name, quantity) VALUES (?, ?, ?)",
            (sku, name, quantity),
        )
        connection.commit()
        item_id = int(cursor.lastrowid)
    item = get_item(database_path, item_id)
    if item is None:  # pragma: no cover - defensive guard for storage corruption
        raise RuntimeError("Created item could not be read back")
    return item


def update_item(
    database_path: str, item_id: int, *, sku: str, name: str, quantity: int
) -> dict[str, Any] | None:
    """Replace an inventory record and return the updated value."""
    with closing(connect(database_path)) as connection:
        cursor = connection.execute(
            """
            UPDATE items
            SET sku = ?, name = ?, quantity = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (sku, name, quantity, item_id),
        )
        connection.commit()
        if cursor.rowcount == 0:
            return None
    return get_item(database_path, item_id)


def delete_item(database_path: str, item_id: int) -> bool:
    """Delete an inventory record and report whether a row changed."""
    with closing(connect(database_path)) as connection:
        cursor = connection.execute("DELETE FROM items WHERE id = ?", (item_id,))
        connection.commit()
    return cursor.rowcount > 0


def database_is_ready(database_path: str) -> bool:
    """Check that the database accepts a simple query."""
    try:
        with closing(connect(database_path)) as connection:
            connection.execute("SELECT 1").fetchone()
        return True
    except sqlite3.Error:
        return False
