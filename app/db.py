from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .daco_client import PriceSnapshot


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path) -> None:
    with _connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                observed_at TEXT NOT NULL,
                source_updated_at TEXT,
                source_url TEXT NOT NULL,
                data_hash TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS brand_prices (
                snapshot_id INTEGER NOT NULL,
                brand TEXT NOT NULL,
                regular REAL NOT NULL,
                premium REAL NOT NULL,
                diesel REAL NOT NULL,
                PRIMARY KEY (snapshot_id, brand),
                FOREIGN KEY (snapshot_id) REFERENCES snapshots(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_brand_prices_brand ON brand_prices(brand);
            CREATE INDEX IF NOT EXISTS idx_snapshots_observed_at ON snapshots(observed_at);
            """
        )


def _hash_snapshot(snapshot: PriceSnapshot) -> str:
    payload = {
        "source_updated_at": snapshot.source_updated_at.isoformat() if snapshot.source_updated_at else None,
        "prices": [
            {
                "brand": p.brand,
                "regular": round(p.regular, 4),
                "premium": round(p.premium, 4),
                "diesel": round(p.diesel, 4),
            }
            for p in sorted(snapshot.prices, key=lambda x: x.brand.lower())
        ],
    }
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def insert_snapshot_if_changed(db_path: Path, snapshot: PriceSnapshot) -> tuple[bool, int | None]:
    data_hash = _hash_snapshot(snapshot)
    observed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    source_updated_at = snapshot.source_updated_at.isoformat() if snapshot.source_updated_at else None

    with _connect(db_path) as conn:
        existing = conn.execute("SELECT id FROM snapshots WHERE data_hash = ?", (data_hash,)).fetchone()
        if existing:
            return False, int(existing["id"])

        cur = conn.execute(
            """
            INSERT INTO snapshots (observed_at, source_updated_at, source_url, data_hash)
            VALUES (?, ?, ?, ?)
            """,
            (observed_at, source_updated_at, snapshot.source_url, data_hash),
        )
        snapshot_id = int(cur.lastrowid)

        conn.executemany(
            """
            INSERT INTO brand_prices (snapshot_id, brand, regular, premium, diesel)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (snapshot_id, p.brand, p.regular, p.premium, p.diesel)
                for p in snapshot.prices
            ],
        )

    return True, snapshot_id


def _get_snapshot_by_id(conn: sqlite3.Connection, snapshot_id: int) -> dict | None:
    snap = conn.execute(
        "SELECT id, observed_at, source_updated_at, source_url FROM snapshots WHERE id = ?",
        (snapshot_id,),
    ).fetchone()
    if not snap:
        return None

    prices_rows = conn.execute(
        """
        SELECT brand, regular, premium, diesel
        FROM brand_prices
        WHERE snapshot_id = ?
        ORDER BY brand COLLATE NOCASE ASC
        """,
        (snapshot_id,),
    ).fetchall()

    return {
        "id": int(snap["id"]),
        "observed_at": snap["observed_at"],
        "source_updated_at": snap["source_updated_at"],
        "source_url": snap["source_url"],
        "prices": [
            {
                "brand": r["brand"],
                "regular": r["regular"],
                "premium": r["premium"],
                "diesel": r["diesel"],
            }
            for r in prices_rows
        ],
    }


def get_latest_snapshot(db_path: Path) -> dict | None:
    with _connect(db_path) as conn:
        row = conn.execute("SELECT id FROM snapshots ORDER BY observed_at DESC LIMIT 1").fetchone()
        if not row:
            return None
        return _get_snapshot_by_id(conn, int(row["id"]))


def get_previous_snapshot(db_path: Path, latest_snapshot_id: int) -> dict | None:
    with _connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT id
            FROM snapshots
            WHERE id < ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (latest_snapshot_id,),
        ).fetchone()
        if not row:
            return None
        return _get_snapshot_by_id(conn, int(row["id"]))


def get_history(db_path: Path, brand: str, fuel: str, days: int) -> list[dict]:
    if fuel not in {"regular", "premium", "diesel"}:
        raise ValueError("fuel must be regular, premium, or diesel")

    since = datetime.now(timezone.utc) - timedelta(days=max(days, 1))
    since_iso = since.replace(microsecond=0).isoformat()

    with _connect(db_path) as conn:
        rows = conn.execute(
            f"""
            SELECT s.observed_at, s.source_updated_at, b.brand, b.{fuel} AS price
            FROM brand_prices b
            JOIN snapshots s ON s.id = b.snapshot_id
            WHERE lower(b.brand) = lower(?)
              AND s.observed_at >= ?
            ORDER BY s.observed_at ASC
            """,
            (brand, since_iso),
        ).fetchall()

    return [
        {
            "observed_at": r["observed_at"],
            "source_updated_at": r["source_updated_at"],
            "brand": r["brand"],
            "fuel": fuel,
            "price": r["price"],
        }
        for r in rows
    ]
