"""Seed the planner DB with reference and/or demo data.

Usage:
    python -m core.seed            # seed reference data only if empty (safe, non-destructive)
    python -m core.seed --demo     # WIPE everything and load a full fake demo dataset

The demo data is generic/fake — safe to ship in the repo and to show in screenshots.
Dates are relative to "today" so the demo always looks current.
"""
import sys
from datetime import date, timedelta

from dotenv import load_dotenv

load_dotenv()

from core.db import init_db, get_conn
from core import repository as repo

TYPES = [("Major", "major"), ("Day2Day", "d2d")]
CATEGORIES = ["Work", "Personal", "Home", "Errands", "Finance"]


def _iso(offset_days: int = 0) -> str:
    return (date.today() + timedelta(days=offset_days)).isoformat()


# ---------------------------------------------------------------------------
# Reference data (safe, only seeds when a table is empty)
# ---------------------------------------------------------------------------

def seed_config() -> None:
    init_db()
    with get_conn() as conn:
        if conn.execute("SELECT COUNT(*) AS c FROM types").fetchone()["c"] == 0:
            for i, (name, kind) in enumerate(TYPES):
                conn.execute("INSERT INTO types (name, position, kind) VALUES (?, ?, ?)", (name, i, kind))
        if conn.execute("SELECT COUNT(*) AS c FROM categories").fetchone()["c"] == 0:
            for i, name in enumerate(CATEGORIES):
                conn.execute("INSERT INTO categories (name, position) VALUES (?, ?)", (name, i))
    print("Seeded reference data (where empty).")


# ---------------------------------------------------------------------------
# Demo data (destructive: wipes and reloads everything)
# ---------------------------------------------------------------------------

def _wipe() -> None:
    with get_conn() as conn:
        for table in ("updates", "subtasks", "tasks", "events", "types", "categories"):
            conn.execute(f"DELETE FROM {table}")
        conn.execute("DELETE FROM sqlite_sequence")  # reset AUTOINCREMENT counters


def seed_demo() -> None:
    init_db()
    _wipe()

    with get_conn() as conn:
        for i, (name, kind) in enumerate(TYPES):
            conn.execute("INSERT INTO types (name, position, kind) VALUES (?, ?, ?)", (name, i, kind))
        for i, name in enumerate(CATEGORIES):
            conn.execute("INSERT INTO categories (name, position) VALUES (?, ?)", (name, i))

    # --- tasks (capture ids for dependencies/subtasks) ---
    portfolio = repo.add_task("Launch portfolio site", "Work", "Major", "")
    roadmap   = repo.add_task("Plan Q3 roadmap", "Work", "Major", _iso(5))     # begins in 5 days
    taxes     = repo.add_task("File quarterly taxes", "Finance", "Major", _iso(10))
    groceries = repo.add_task("Buy groceries", "Errands", "Day2Day", "")
    emails    = repo.add_task("Reply to emails", "Work", "Day2Day", "")
    plants    = repo.add_task("Water the plants", "Home", "Day2Day", "")
    bank      = repo.add_task("Call the bank", "Finance", "Day2Day", "")
    gym       = repo.add_task("Renew gym membership", "Personal", "Day2Day", "")

    # done states
    repo.update_task_done(emails, True)

    # dependency-based blocking (waiting_on is derived)
    repo.update_task(portfolio, blocked_by=str(roadmap))
    repo.update_task(bank, blocked_by=str(taxes))

    # subtasks (some done)
    sub_design = repo.add_subtask(portfolio, "Finalize design"); repo.update_subtask_done(sub_design, True)
    sub_build  = repo.add_subtask(portfolio, "Build the pages")
    repo.add_subtask(portfolio, "Deploy to hosting")
    repo.add_subtask(groceries, "Milk")
    repo.add_subtask(groceries, "Eggs")
    sub_coffee = repo.add_subtask(groceries, "Coffee beans"); repo.update_subtask_done(sub_coffee, True)

    # update / log threads
    repo.add_update("task", portfolio, "waiting on the final logo from the designer")
    repo.add_update("subtask", sub_build, "hero section done, working on the about page")
    repo.add_update("task", roadmap, "draft shared with the team for feedback")

    # --- calendar events ---
    offsite = repo.add_event("Team offsite", False, _iso(3), _iso(5))
    repo.add_update("event", offsite, "book train tickets + hotel")
    repo.add_event("Dentist appointment", True, _iso(2), _iso(2))
    bday = repo.add_event("Mom's birthday", True, _iso(8), _iso(8))
    repo.add_update("event", bday, "order flowers")
    repo.add_event("Design conference", False, _iso(14), _iso(16))

    print("Loaded demo data: 8 tasks, 6 subtasks, 4 events, "
          f"{len(repo.get_categories())} categories, {len(repo.get_types())} types.")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        seed_demo()
    else:
        seed_config()
