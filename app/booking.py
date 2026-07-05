"""Хранилище записей на SQLite (бесплатно, без внешних сервисов)."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .config import BASE_DIR

DB_PATH = BASE_DIR / "data" / "bookings.db"


@dataclass
class Booking:
    service: str
    name: str
    phone: str
    wanted_time: str
    tg_user: str


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            service TEXT NOT NULL,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            wanted_time TEXT NOT NULL,
            tg_user TEXT
        )
        """
    )
    return conn


def save_booking(b: Booking) -> int:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO bookings (created_at, service, name, phone, wanted_time, tg_user)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (datetime.now().isoformat(timespec="seconds"), b.service, b.name, b.phone,
             b.wanted_time, b.tg_user),
        )
        return int(cur.lastrowid)
