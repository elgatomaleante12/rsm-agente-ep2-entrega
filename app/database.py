from __future__ import annotations

import csv
import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_DB_PATH = DATA_DIR / "rsm_agent.db"


def db_path() -> Path:
    configured = os.getenv("RSM_DB_PATH")
    if configured:
        return Path(configured).expanduser().resolve()
    return DEFAULT_DB_PATH


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(path: Path | None = None) -> sqlite3.Connection:
    path = path or db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(reset: bool = False, path: Path | None = None) -> Path:
    path = path or db_path()
    if reset and path.exists():
        path.unlink()

    with closing(connect(path)) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS inventory (
                ref TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                stock INTEGER NOT NULL,
                min_stock INTEGER NOT NULL,
                location TEXT NOT NULL,
                provider TEXT NOT NULL,
                lead_time_days INTEGER NOT NULL,
                compatible_models TEXT NOT NULL,
                last_update TEXT NOT NULL,
                unit_price REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_ref TEXT NOT NULL REFERENCES inventory(ref),
                quantity INTEGER NOT NULL,
                movement_type TEXT NOT NULL CHECK(movement_type IN ('entrada', 'salida', 'ajuste')),
                ot_id TEXT,
                mechanic TEXT,
                vehicle TEXT,
                note TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                source TEXT NOT NULL
            );
            """
        )
        if _table_count(conn, "inventory") == 0:
            _seed_inventory(conn)
        if _table_count(conn, "knowledge") == 0:
            _seed_knowledge(conn)
        conn.commit()
    return path


def _table_count(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _seed_inventory(conn: sqlite3.Connection) -> None:
    with (DATA_DIR / "inventory.csv").open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            conn.execute(
                """
                INSERT INTO inventory (
                    ref, name, category, stock, min_stock, location, provider,
                    lead_time_days, compatible_models, last_update, unit_price
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["ref"],
                    row["name"],
                    row["category"],
                    int(row["stock"]),
                    int(row["min_stock"]),
                    row["location"],
                    row["provider"],
                    int(row["lead_time_days"]),
                    row["compatible_models"],
                    row["last_update"],
                    float(row["unit_price"]),
                ),
            )


def _seed_knowledge(conn: sqlite3.Connection) -> None:
    records = json.loads((DATA_DIR / "knowledge_base.json").read_text(encoding="utf-8"))
    for row in records:
        conn.execute(
            "INSERT INTO knowledge (title, content, source) VALUES (?, ?, ?)",
            (row["title"], row["content"], row["source"]),
        )


def rows(query: str, params: tuple[Any, ...] = (), path: Path | None = None) -> list[dict[str, Any]]:
    with closing(connect(path)) as conn:
        return [dict(row) for row in conn.execute(query, params).fetchall()]


def one(query: str, params: tuple[Any, ...] = (), path: Path | None = None) -> dict[str, Any] | None:
    with closing(connect(path)) as conn:
        row = conn.execute(query, params).fetchone()
        return dict(row) if row else None


def add_memory(
    session_id: str,
    kind: str,
    content: str,
    metadata: dict[str, Any] | None = None,
    path: Path | None = None,
) -> None:
    with closing(connect(path)) as conn:
        conn.execute(
            """
            INSERT INTO memory (session_id, kind, content, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, kind, content, json.dumps(metadata or {}, ensure_ascii=False), utc_now()),
        )
        conn.commit()


def get_recent_memory(session_id: str, limit: int = 8, path: Path | None = None) -> list[dict[str, Any]]:
    return rows(
        """
        SELECT kind, content, metadata_json, created_at
        FROM memory
        WHERE session_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (session_id, limit),
        path,
    )


def register_movement(
    item_ref: str,
    quantity: int,
    movement_type: str,
    ot_id: str | None,
    mechanic: str | None,
    vehicle: str | None,
    note: str | None = None,
    path: Path | None = None,
) -> dict[str, Any]:
    if quantity <= 0:
        raise ValueError("La cantidad debe ser mayor que cero.")
    if movement_type not in {"entrada", "salida", "ajuste"}:
        raise ValueError("Tipo de movimiento no valido.")

    with closing(connect(path)) as conn:
        item = conn.execute("SELECT * FROM inventory WHERE ref = ?", (item_ref,)).fetchone()
        if not item:
            raise ValueError(f"No existe el item {item_ref}.")

        current = int(item["stock"])
        if movement_type == "salida" and current < quantity:
            return {
                "ok": False,
                "reason": "stock_insuficiente",
                "item": dict(item),
                "requested": quantity,
                "available": current,
            }

        if movement_type == "entrada":
            next_stock = current + quantity
        elif movement_type == "salida":
            next_stock = current - quantity
        else:
            next_stock = quantity

        conn.execute("UPDATE inventory SET stock = ?, last_update = ? WHERE ref = ?", (next_stock, utc_now(), item_ref))
        conn.execute(
            """
            INSERT INTO movements (item_ref, quantity, movement_type, ot_id, mechanic, vehicle, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (item_ref, quantity, movement_type, ot_id, mechanic, vehicle, note, utc_now()),
        )
        updated = conn.execute("SELECT * FROM inventory WHERE ref = ?", (item_ref,)).fetchone()
        conn.commit()
        return {
            "ok": True,
            "item": dict(updated),
            "previous_stock": current,
            "new_stock": next_stock,
            "below_minimum": next_stock <= int(updated["min_stock"]),
        }
