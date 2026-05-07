import sqlite3
import os
import threading
from datetime import date

DB_DIR = os.path.expanduser("~/Library/Application Support/HabitTracker")
DB_PATH = os.path.join(DB_DIR, "habits.db")

_local = threading.local()


def _conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn"):
        os.makedirs(DB_DIR, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        _local.conn = conn
    return _local.conn


def init_db():
    with _conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS habits (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                year  INTEGER NOT NULL,
                month INTEGER NOT NULL,
                name  TEXT    NOT NULL,
                icon  TEXT    NOT NULL DEFAULT '',
                ord   INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS records (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                habit_id INTEGER NOT NULL REFERENCES habits(id) ON DELETE CASCADE,
                date     TEXT    NOT NULL,
                done     INTEGER NOT NULL DEFAULT 0,
                UNIQUE(habit_id, date)
            );
            CREATE TABLE IF NOT EXISTS game_log (
                date  TEXT PRIMARY KEY,
                count INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL DEFAULT ''
            );
        """)
    # Migration for existing databases without the icon column
    try:
        with _conn() as conn:
            conn.execute("ALTER TABLE habits ADD COLUMN icon TEXT NOT NULL DEFAULT ''")
    except Exception:
        pass


# ── Habits ────────────────────────────────────────────────────────────────────

def get_habits(year: int, month: int) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM habits WHERE year=? AND month=? ORDER BY ord",
            (year, month),
        ).fetchall()
    return [dict(r) for r in rows]


def add_habits_batch(year: int, month: int, names: list[str]):
    with _conn() as conn:
        max_ord = conn.execute(
            "SELECT COALESCE(MAX(ord), -1) FROM habits WHERE year=? AND month=?",
            (year, month),
        ).fetchone()[0]
        conn.executemany(
            "INSERT INTO habits (year, month, name, ord) VALUES (?,?,?,?)",
            [(year, month, name, max_ord + 1 + i) for i, name in enumerate(names)],
        )


def add_habit(year: int, month: int, name: str) -> int:
    with _conn() as conn:
        max_ord = conn.execute(
            "SELECT COALESCE(MAX(ord), -1) FROM habits WHERE year=? AND month=?",
            (year, month),
        ).fetchone()[0]
        cur = conn.execute(
            "INSERT INTO habits (year, month, name, ord) VALUES (?,?,?,?)",
            (year, month, name, max_ord + 1),
        )
        return cur.lastrowid


def rename_habit(habit_id: int, new_name: str):
    with _conn() as conn:
        conn.execute("UPDATE habits SET name=? WHERE id=?", (new_name, habit_id))


def set_habit_icon(habit_id: int, icon_name: str):
    with _conn() as conn:
        conn.execute("UPDATE habits SET icon=? WHERE id=?", (icon_name, habit_id))


def remove_habit(habit_id: int):
    with _conn() as conn:
        conn.execute("DELETE FROM habits WHERE id=?", (habit_id,))


def reorder_habits(habit_ids: list[int]):
    with _conn() as conn:
        for i, hid in enumerate(habit_ids):
            conn.execute("UPDATE habits SET ord=? WHERE id=?", (i, hid))


def copy_habits_from_month(fy: int, fm: int, ty: int, tm: int):
    src = get_habits(fy, fm)
    with _conn() as conn:
        conn.execute("DELETE FROM habits WHERE year=? AND month=?", (ty, tm))
        for h in src:
            conn.execute(
                "INSERT INTO habits (year, month, name, icon, ord) VALUES (?,?,?,?,?)",
                (ty, tm, h["name"], h.get("icon", ""), h["ord"]),
            )


# ── Records ───────────────────────────────────────────────────────────────────

def get_record(habit_id: int, date_str: str) -> bool:
    with _conn() as conn:
        row = conn.execute(
            "SELECT done FROM records WHERE habit_id=? AND date=?",
            (habit_id, date_str),
        ).fetchone()
    return bool(row["done"]) if row else False


def set_record(habit_id: int, date_str: str, done: bool):
    with _conn() as conn:
        conn.execute(
            "INSERT INTO records (habit_id, date, done) VALUES (?,?,?) "
            "ON CONFLICT(habit_id, date) DO UPDATE SET done=excluded.done",
            (habit_id, date_str, int(done)),
        )


def toggle_record(habit_id: int, date_str: str) -> bool:
    with _conn() as conn:
        row = conn.execute(
            "SELECT done FROM records WHERE habit_id=? AND date=?",
            (habit_id, date_str),
        ).fetchone()
        new = not (bool(row["done"]) if row else False)
        conn.execute(
            "INSERT INTO records (habit_id, date, done) VALUES (?,?,?) "
            "ON CONFLICT(habit_id, date) DO UPDATE SET done=excluded.done",
            (habit_id, date_str, int(new)),
        )
    return new


def get_monthly_records(year: int, month: int) -> dict[int, dict[str, bool]]:
    habits = get_habits(year, month)
    if not habits:
        return {}
    ids = [h["id"] for h in habits]
    ph = ",".join("?" * len(ids))
    with _conn() as conn:
        rows = conn.execute(
            f"SELECT habit_id, date, done FROM records WHERE habit_id IN ({ph})",
            ids,
        ).fetchall()
    result: dict[int, dict[str, bool]] = {h["id"]: {} for h in habits}
    for r in rows:
        result[r["habit_id"]][r["date"]] = bool(r["done"])
    return result


# ── Game log ──────────────────────────────────────────────────────────────────

def get_game_count(date_str: str) -> int:
    with _conn() as conn:
        row = conn.execute(
            "SELECT count FROM game_log WHERE date=?", (date_str,)
        ).fetchone()
    return row["count"] if row else 0


def set_game_count(date_str: str, count: int):
    with _conn() as conn:
        conn.execute(
            "INSERT INTO game_log (date, count) VALUES (?,?) "
            "ON CONFLICT(date) DO UPDATE SET count=excluded.count",
            (date_str, count),
        )


def get_setting(key: str, default: str = "") -> str:
    with _conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str):
    with _conn() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )


def get_monthly_game_counts(year: int, month: int) -> dict[str, int]:
    prefix = f"{year:04d}-{month:02d}"
    with _conn() as conn:
        rows = conn.execute(
            "SELECT date, count FROM game_log WHERE date LIKE ?",
            (f"{prefix}-%",),
        ).fetchall()
    return {r["date"]: r["count"] for r in rows}
