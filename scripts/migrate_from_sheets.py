"""One-time migration: pull existing data from Google Sheets into SQLite.

Reads the live spreadsheet via the old bot.sheets layer and writes Tasks,
Subtasks, Types and Categories into the new SQLite DB, PRESERVING original
task/subtask ids so that `blocked_by` references stay valid.

Usage:
    python -m scripts.migrate_from_sheets            # migrate into DB_PATH
    python -m scripts.migrate_from_sheets --reset    # wipe tables first

Requires SPREADSHEET_ID and GOOGLE_CREDS_JSON in the environment / .env.
"""
import sys

from dotenv import load_dotenv

load_dotenv()

from config.settings import config
from core.db import init_db, get_conn
from bot import sheets


def _truthy(v: str) -> int:
    return 1 if str(v).strip().upper() == "TRUE" else 0


def _reset(conn) -> None:
    for table in ("subtasks", "tasks", "types", "categories"):
        conn.execute(f"DELETE FROM {table}")


def migrate(reset: bool = False) -> None:
    if not config.spreadsheet_id or not config.google_creds:
        sys.exit("SPREADSHEET_ID and GOOGLE_CREDS_JSON must be set to migrate.")

    print("Reading from Google Sheets...")
    tasks = sheets.get_all_tasks()
    subtasks = sheets.get_all_subtasks()
    types = sheets.get_types()
    categories = sheets.get_categories()
    print(f"  {len(tasks)} tasks, {len(subtasks)} subtasks, "
          f"{len(types)} types, {len(categories)} categories")

    init_db()
    with get_conn() as conn:
        if reset:
            _reset(conn)

        for i, name in enumerate(types):
            conn.execute(
                "INSERT OR IGNORE INTO types (name, position) VALUES (?, ?)", (name, i)
            )
        for i, name in enumerate(categories):
            conn.execute(
                "INSERT OR IGNORE INTO categories (name, position) VALUES (?, ?)", (name, i)
            )

        for t in tasks:
            if not t.get("ID", "").isdigit() or not t.get("Title", "").strip():
                continue  # skip blank/pre-numbered rows with no title
            conn.execute(
                "INSERT OR REPLACE INTO tasks "
                "(id, title, category, type, done, date, blocked_by) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    int(t["ID"]),
                    t.get("Title", ""),
                    t.get("Category", ""),
                    t.get("Type", ""),
                    _truthy(t.get("Done", "FALSE")),
                    t.get("Date", ""),
                    t.get("Blocked By", ""),
                ),
            )

        for s in subtasks:
            if not s.get("ID", "").isdigit() or not s.get("Task ID", "").isdigit():
                continue
            conn.execute(
                "INSERT OR REPLACE INTO subtasks (id, task_id, title, done) "
                "VALUES (?, ?, ?, ?)",
                (
                    int(s["ID"]),
                    int(s["Task ID"]),
                    s.get("Title", ""),
                    _truthy(s.get("Done", "FALSE")),
                ),
            )

    print(f"Migration complete -> {config.db_path}")


if __name__ == "__main__":
    migrate(reset="--reset" in sys.argv)
