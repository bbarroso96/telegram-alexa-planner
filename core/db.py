import os
import sqlite3
from contextlib import contextmanager

from config.settings import config


SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT    NOT NULL,
    category   TEXT    DEFAULT '',
    type       TEXT    DEFAULT '',
    done       INTEGER NOT NULL DEFAULT 0,   -- 0 = open, 1 = done
    date       TEXT    DEFAULT '',           -- 'YYYY-MM-DD' or '' (open)
    blocked_by TEXT    DEFAULT '',           -- comma-separated task ids
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_tasks_done ON tasks(done);

CREATE TABLE IF NOT EXISTS subtasks (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    title   TEXT    NOT NULL,
    done    INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_subtasks_task ON subtasks(task_id);

CREATE TABLE IF NOT EXISTS types (
    name     TEXT PRIMARY KEY,
    position INTEGER,
    kind     TEXT             -- stable role: 'major' | 'd2d' (survives renames)
);

CREATE TABLE IF NOT EXISTS categories (
    name     TEXT PRIMARY KEY,
    position INTEGER
);

CREATE TABLE IF NOT EXISTS events (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT    NOT NULL,
    single INTEGER NOT NULL DEFAULT 1,   -- 1 = one day, 0 = range
    start  TEXT    NOT NULL,             -- 'YYYY-MM-DD'
    end    TEXT    NOT NULL              -- 'YYYY-MM-DD' (== start when single)
);
CREATE INDEX IF NOT EXISTS idx_events_start ON events(start);

-- Threaded update/comment messages for tasks, subtasks and events.
CREATE TABLE IF NOT EXISTS updates (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    target_type TEXT    NOT NULL,        -- 'task' | 'subtask' | 'event'
    target_id   INTEGER NOT NULL,
    ts          TEXT    NOT NULL,        -- 'YYYY-MM-DD HH:MM'
    text        TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_updates_target ON updates(target_type, target_id);
"""


def connect() -> sqlite3.Connection:
    db_dir = os.path.dirname(config.db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(config.db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # bot + web API can share the file
    conn.execute("PRAGMA busy_timeout=5000")  # wait out the other process's writes
    conn.execute("PRAGMA foreign_keys=ON")    # cascade subtask deletes
    return conn


@contextmanager
def get_conn():
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _migrate_types_kind(conn) -> None:
    """Add types.kind to pre-existing DBs and backfill from the canonical names."""
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(types)")]
    if "kind" not in cols:
        conn.execute("ALTER TABLE types ADD COLUMN kind TEXT")
    # Backfill any rows missing a kind: 'Major' -> major, everything else -> d2d.
    for r in conn.execute("SELECT name FROM types WHERE kind IS NULL OR kind = ''").fetchall():
        kind = "major" if r["name"].strip().lower() == "major" else "d2d"
        conn.execute("UPDATE types SET kind = ? WHERE name = ?", (kind, r["name"]))


def init_db() -> None:
    """Create tables if they don't exist. Safe to call on every startup."""
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        _migrate_types_kind(conn)
