"""SQLite data layer for the planner.

Read functions return dicts in the SAME shape the old Google Sheets layer
produced (string keys "ID"/"Title"/..., "Done" as "TRUE"/"FALSE") so the bot
and Alexa code can use this module as a drop-in replacement for bot.sheets.
"""
from datetime import datetime

from core.db import get_conn


def _now_stamp() -> str:
    """Timestamp in the design's 'YYYY-MM-DD HH:MM' format."""
    return datetime.now().strftime("%Y-%m-%d %H:%M")


# ---------------------------------------------------------------------------
# Row -> legacy-dict adapters
# ---------------------------------------------------------------------------

def _task_dict(r) -> dict:
    return {
        "ID": str(r["id"]),
        "Title": r["title"],
        "Category": r["category"] or "",
        "Type": r["type"] or "",
        "Done": "TRUE" if r["done"] else "FALSE",
        "Date": r["date"] or "",
        "Blocked By": r["blocked_by"] or "",
        "CreatedAt": r["created_at"] or "",
    }


def _subtask_dict(r) -> dict:
    return {
        "ID": str(r["id"]),
        "Task ID": str(r["task_id"]),
        "Title": r["title"],
        "Done": "TRUE" if r["done"] else "FALSE",
    }


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

# Order types with the 'major' role first, so callers can treat [0] as the
# high-priority section and [1] as routine regardless of the actual names.
_KIND_ORDER = "CASE kind WHEN 'major' THEN 0 ELSE 1 END, position IS NULL, position, rowid"


def get_types() -> list[str]:
    with get_conn() as conn:
        rows = conn.execute(f"SELECT name FROM types ORDER BY {_KIND_ORDER}").fetchall()
    return [r["name"] for r in rows if r["name"]]


def get_types_full() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(f"SELECT name, kind FROM types ORDER BY {_KIND_ORDER}").fetchall()
    return [{"name": r["name"], "kind": r["kind"] or "d2d"} for r in rows if r["name"]]


def major_type_name() -> str:
    """Current display name of the high-priority ('major') type."""
    with get_conn() as conn:
        r = conn.execute(
            "SELECT name FROM types WHERE kind = 'major' ORDER BY position IS NULL, position LIMIT 1"
        ).fetchone()
    return r["name"] if r else "Major"


def type_name_for_kind(kind: str) -> str:
    with get_conn() as conn:
        r = conn.execute(
            "SELECT name FROM types WHERE kind = ? ORDER BY position IS NULL, position LIMIT 1",
            (kind,),
        ).fetchone()
    return r["name"] if r else kind


def kind_for_type_name(name: str) -> str:
    with get_conn() as conn:
        r = conn.execute("SELECT kind FROM types WHERE name = ?", (name,)).fetchone()
    return r["kind"] if r and r["kind"] else "d2d"


def get_categories() -> list[str]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT name FROM categories ORDER BY position IS NULL, position, rowid"
        ).fetchall()
    return [r["name"] for r in rows if r["name"]]


def add_type(name: str, kind: str = "d2d") -> None:
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO types (name, kind) VALUES (?, ?)", (name.strip(), kind))


def add_category(name: str) -> None:
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (name.strip(),))


def delete_type(name: str) -> int:
    with get_conn() as conn:
        return conn.execute("DELETE FROM types WHERE name = ?", (name,)).rowcount


def rename_type(old: str, new: str) -> None:
    """Rename a type (keeping its kind/role) and cascade to every task using it."""
    new = new.strip()
    if not new or new == old:
        return
    with get_conn() as conn:
        exists = conn.execute("SELECT 1 FROM types WHERE name = ?", (new,)).fetchone()
        if exists:
            conn.execute("DELETE FROM types WHERE name = ?", (old,))
        else:
            conn.execute("UPDATE types SET name = ? WHERE name = ?", (new, old))
        conn.execute("UPDATE tasks SET type = ? WHERE type = ?", (new, old))


def delete_category(name: str) -> int:
    with get_conn() as conn:
        return conn.execute("DELETE FROM categories WHERE name = ?", (name,)).rowcount


def rename_category(old: str, new: str) -> None:
    """Rename a category and cascade to every task that uses it. If `new` already
    exists, the two are merged (old is removed, its tasks reassigned to new)."""
    new = new.strip()
    if not new or new == old:
        return
    with get_conn() as conn:
        exists = conn.execute("SELECT 1 FROM categories WHERE name = ?", (new,)).fetchone()
        if exists:
            conn.execute("DELETE FROM categories WHERE name = ?", (old,))
        else:
            conn.execute("UPDATE categories SET name = ? WHERE name = ?", (new, old))
        conn.execute("UPDATE tasks SET category = ? WHERE category = ?", (new, old))


# ---------------------------------------------------------------------------
# Tasks — reads
# ---------------------------------------------------------------------------

def get_all_tasks() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()
    return [_task_dict(r) for r in rows]


def get_task_by_id(task_id: int) -> dict | None:
    with get_conn() as conn:
        r = conn.execute("SELECT * FROM tasks WHERE id = ?", (int(task_id),)).fetchone()
    return _task_dict(r) if r else None


# ---------------------------------------------------------------------------
# Tasks — writes
# ---------------------------------------------------------------------------

def add_task(title: str, category: str, type_: str, date_str: str = "",
             blocked_by: str = "") -> int:
    """Insert a task; returns the new auto-assigned id."""
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO tasks (title, category, type, date, blocked_by) "
            "VALUES (?, ?, ?, ?, ?)",
            (title, category, type_, date_str, blocked_by),
        )
        return cur.lastrowid


def update_task(task_id: int, *, title: str | None = None, category: str | None = None,
                type_: str | None = None, date_str: str | None = None,
                blocked_by: str | None = None) -> int:
    """Patch any subset of a task's fields. Returns rows affected."""
    fields, params = [], []
    for col, val in (("title", title), ("category", category), ("type", type_),
                     ("date", date_str), ("blocked_by", blocked_by)):
        if val is not None:
            fields.append(f"{col} = ?")
            params.append(val)
    if not fields:
        return 0
    params.append(int(task_id))
    with get_conn() as conn:
        return conn.execute(
            f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?", params
        ).rowcount


def update_task_done(task_id: int, done: bool) -> bool:
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE tasks SET done = ? WHERE id = ?", (1 if done else 0, int(task_id))
        )
        return cur.rowcount > 0


def delete_task(task_id: int) -> int:
    with get_conn() as conn:
        sub_ids = [r["id"] for r in conn.execute(
            "SELECT id FROM subtasks WHERE task_id = ?", (int(task_id),)
        ).fetchall()]
        conn.execute(
            "DELETE FROM updates WHERE target_type = 'task' AND target_id = ?", (int(task_id),)
        )
        for sid in sub_ids:
            conn.execute(
                "DELETE FROM updates WHERE target_type = 'subtask' AND target_id = ?", (sid,)
            )
        # subtasks themselves cascade via the FK
        return conn.execute("DELETE FROM tasks WHERE id = ?", (int(task_id),)).rowcount


# ---------------------------------------------------------------------------
# Subtasks
# ---------------------------------------------------------------------------

def get_all_subtasks() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM subtasks ORDER BY id").fetchall()
    return [_subtask_dict(r) for r in rows]


def get_subtasks_for(task_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM subtasks WHERE task_id = ? ORDER BY id", (int(task_id),)
        ).fetchall()
    return [_subtask_dict(r) for r in rows]


def add_subtask(task_id: int, title: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO subtasks (task_id, title) VALUES (?, ?)", (int(task_id), title)
        )
        return cur.lastrowid


def update_subtask_done(subtask_id: int, done: bool) -> bool:
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE subtasks SET done = ? WHERE id = ?",
            (1 if done else 0, int(subtask_id)),
        )
        return cur.rowcount > 0


def delete_subtask(subtask_id: int) -> int:
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM updates WHERE target_type = 'subtask' AND target_id = ?",
            (int(subtask_id),),
        )
        return conn.execute(
            "DELETE FROM subtasks WHERE id = ?", (int(subtask_id),)
        ).rowcount


# ---------------------------------------------------------------------------
# Update / comment threads (tasks, subtasks, events)
# ---------------------------------------------------------------------------

def add_update(target_type: str, target_id: int, text: str) -> dict:
    """Append a threaded message; returns {id, ts, text}."""
    ts = _now_stamp()
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO updates (target_type, target_id, ts, text) VALUES (?, ?, ?, ?)",
            (target_type, int(target_id), ts, text),
        )
        return {"id": cur.lastrowid, "ts": ts, "text": text}


def get_updates(target_type: str, target_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, ts, text FROM updates WHERE target_type = ? AND target_id = ? "
            "ORDER BY id",
            (target_type, int(target_id)),
        ).fetchall()
    return [{"id": r["id"], "ts": r["ts"], "text": r["text"]} for r in rows]


def get_all_updates() -> list[dict]:
    """All threads at once, for efficient serialization of the full task/event list."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, target_type, target_id, ts, text FROM updates ORDER BY id"
        ).fetchall()
    return [
        {"id": r["id"], "target_type": r["target_type"], "target_id": r["target_id"],
         "ts": r["ts"], "text": r["text"]}
        for r in rows
    ]


def delete_update(update_id: int) -> int:
    with get_conn() as conn:
        return conn.execute("DELETE FROM updates WHERE id = ?", (int(update_id),)).rowcount


# ---------------------------------------------------------------------------
# Calendar events
# ---------------------------------------------------------------------------

def _event_row(r) -> dict:
    return {
        "id": r["id"],
        "title": r["title"],
        "single": bool(r["single"]),
        "start": r["start"],
        "end": r["end"],
    }


def get_all_events() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM events ORDER BY start, id").fetchall()
    return [_event_row(r) for r in rows]


def get_event(event_id: int) -> dict | None:
    with get_conn() as conn:
        r = conn.execute("SELECT * FROM events WHERE id = ?", (int(event_id),)).fetchone()
    return _event_row(r) if r else None


def add_event(title: str, single: bool, start: str, end: str) -> int:
    if not single and end < start:
        start, end = end, start
    if single:
        end = start
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO events (title, single, start, end) VALUES (?, ?, ?, ?)",
            (title, 1 if single else 0, start, end),
        )
        return cur.lastrowid


def update_event(event_id: int, *, title: str | None = None, single: bool | None = None,
                 start: str | None = None, end: str | None = None) -> int:
    fields, params = [], []
    if title is not None:
        fields.append("title = ?"); params.append(title)
    if single is not None:
        fields.append("single = ?"); params.append(1 if single else 0)
    if start is not None:
        fields.append("start = ?"); params.append(start)
    if end is not None:
        fields.append("end = ?"); params.append(end)
    if not fields:
        return 0
    params.append(int(event_id))
    with get_conn() as conn:
        return conn.execute(
            f"UPDATE events SET {', '.join(fields)} WHERE id = ?", params
        ).rowcount


def delete_event(event_id: int) -> int:
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM updates WHERE target_type = 'event' AND target_id = ?",
            (int(event_id),),
        )
        return conn.execute("DELETE FROM events WHERE id = ?", (int(event_id),)).rowcount
