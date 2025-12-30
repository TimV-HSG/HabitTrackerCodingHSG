"""
SQLite layer for the habit tracker.

The app keeps a tiny schema on disk so data survives restarts.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from typing import Iterable, Optional, Sequence, Tuple

DB_PATH_DEFAULT = os.path.join("data", "habits.db")


def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


@contextmanager
def connect(db_path: str = DB_PATH_DEFAULT):
    _ensure_parent_dir(db_path)
    conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: str = DB_PATH_DEFAULT) -> None:
    """
    Create tables if they don't exist yet.
    """
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS habits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT DEFAULT '',
                schedule_type TEXT NOT NULL DEFAULT 'daily',
                custom_days TEXT DEFAULT '',         -- comma-separated 0..6 (Mon..Sun)
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS checkins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                habit_id INTEGER NOT NULL,
                day TEXT NOT NULL,                  -- YYYY-MM-DD
                done INTEGER NOT NULL DEFAULT 1,
                note TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                UNIQUE(habit_id, day),
                FOREIGN KEY (habit_id) REFERENCES habits(id) ON DELETE CASCADE
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )

        conn.execute("PRAGMA foreign_keys = ON")


# --- Habit CRUD ---------------------------------------------------------------

def list_habits(db_path: str = DB_PATH_DEFAULT):
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT id, name, description, schedule_type, custom_days, created_at FROM habits ORDER BY name"
        ).fetchall()
    return [dict(r) for r in rows]


def get_habit(habit_id: int, db_path: str = DB_PATH_DEFAULT):
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT id, name, description, schedule_type, custom_days, created_at FROM habits WHERE id = ?",
            (habit_id,),
        ).fetchone()
    return dict(row) if row else None


def create_habit(
    name: str,
    description: str,
    schedule_type: str,
    custom_days: str,
    created_at: str,
    db_path: str = DB_PATH_DEFAULT,
) -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO habits (name, description, schedule_type, custom_days, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name.strip(), description.strip(), schedule_type, custom_days.strip(), created_at),
        )


def update_habit(
    habit_id: int,
    name: str,
    description: str,
    schedule_type: str,
    custom_days: str,
    db_path: str = DB_PATH_DEFAULT,
) -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            UPDATE habits
               SET name = ?, description = ?, schedule_type = ?, custom_days = ?
             WHERE id = ?
            """,
            (name.strip(), description.strip(), schedule_type, custom_days.strip(), habit_id),
        )


def delete_habit(habit_id: int, db_path: str = DB_PATH_DEFAULT) -> None:
    with connect(db_path) as conn:
        conn.execute("DELETE FROM habits WHERE id = ?", (habit_id,))


# --- Check-ins ---------------------------------------------------------------

def upsert_checkin(
    habit_id: int,
    day: str,
    done: bool,
    note: str,
    created_at: str,
    db_path: str = DB_PATH_DEFAULT,
) -> None:
    """
    Create or update the check-in for (habit, day).
    """
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO checkins (habit_id, day, done, note, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(habit_id, day) DO UPDATE SET
                done=excluded.done,
                note=excluded.note
            """,
            (habit_id, day, 1 if done else 0, note.strip(), created_at),
        )


def get_checkin(habit_id: int, day: str, db_path: str = DB_PATH_DEFAULT):
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT id, habit_id, day, done, note, created_at FROM checkins WHERE habit_id = ? AND day = ?",
            (habit_id, day),
        ).fetchone()
    return dict(row) if row else None


def list_checkins_for_habit(habit_id: int, db_path: str = DB_PATH_DEFAULT):
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT day, done, note FROM checkins WHERE habit_id = ? ORDER BY day",
            (habit_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def list_checkins_between(start_day: str, end_day: str, db_path: str = DB_PATH_DEFAULT):
    """
    Return all check-ins where start_day <= day <= end_day (inclusive).
    """
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT habit_id, day, done, note
              FROM checkins
             WHERE day >= ? AND day <= ?
            """,
            (start_day, end_day),
        ).fetchall()
    return [dict(r) for r in rows]


# --- Settings ----------------------------------------------------------------

def get_setting(key: str, default: str = "", db_path: str = DB_PATH_DEFAULT) -> str:
    with connect(db_path) as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return str(row["value"]) if row else default


def set_setting(key: str, value: str, db_path: str = DB_PATH_DEFAULT) -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """,
            (key, str(value)),
        )
