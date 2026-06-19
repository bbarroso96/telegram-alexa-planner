from datetime import date
from core import repository as sheets


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_blocked_by(raw: str) -> list[int]:
    if not raw or not raw.strip():
        return []
    return [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]


def _task_is_blocked(task: dict, all_tasks: list[dict]) -> bool:
    blocker_ids = _parse_blocked_by(task.get("Blocked By", ""))
    if not blocker_ids:
        return False
    done_ids = {int(t["ID"]) for t in all_tasks if t.get("Done", "").upper() == "TRUE"}
    return any(bid not in done_ids for bid in blocker_ids)


def _format_date(date_str: str) -> str:
    if not date_str:
        return "open"
    try:
        from datetime import datetime
        d = datetime.strptime(date_str, "%Y-%m-%d")
        months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
        return f"{months[d.month - 1]} {d.day}"
    except Exception:
        return date_str


def format_single_task(task: dict, subtasks: list[dict] | None = None, all_tasks: list[dict] | None = None) -> str:
    if all_tasks is None:
        all_tasks = sheets.get_all_tasks()

    blocked = _task_is_blocked(task, all_tasks)

    blocker_ids = _parse_blocked_by(task.get("Blocked By", ""))
    active_blocker_names = []
    if blocker_ids:
        id_to_task = {int(t["ID"]): t for t in all_tasks if t.get("ID", "").isdigit()}
        active_blocker_names = [
            id_to_task[bid]["Title"]
            for bid in blocker_ids
            if id_to_task.get(bid, {}).get("Done", "FALSE").upper() == "FALSE"
        ]

    title = f"• [blocked] {task['Title']}" if blocked else f"• {task['Title']}"
    date_str = _format_date(task.get("Date", ""))
    category = task.get("Category", "")
    meta = f"{category} · {date_str}" if category else date_str

    lines = [
        f"*{title}*",
        f"_{meta}_",
    ]

    if active_blocker_names:
        lines.append(f"Waiting on: {', '.join(active_blocker_names)}")

    if subtasks:
        for st in subtasks:
            st_done = st.get("Done", "FALSE").upper() == "TRUE"
            prefix = "  ✅ " if st_done else "  ⬜ "
            lines.append(f"{prefix}{st['Title']}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

def get_today_task_list() -> list[dict]:
    today_str = date.today().isoformat()
    major_name = sheets.major_type_name()
    all_tasks = sheets.get_all_tasks()
    return [
        t for t in all_tasks
        if t.get("Done", "FALSE").upper() == "FALSE"
        and t.get("Type", "") != major_name
        and (not t.get("Date") or t.get("Date") <= today_str)
    ]


def get_pending_task_list() -> list[dict]:
    all_tasks = sheets.get_all_tasks()
    return [t for t in all_tasks if t.get("Done", "FALSE").upper() == "FALSE"]


def get_today_tasks() -> str:
    tasks_list = get_today_task_list()
    if not tasks_list:
        return "No daily tasks for today 🎉"
    today_str = date.today().isoformat()
    all_subtasks = sheets.get_all_subtasks()
    subtasks_by_task = {}
    for st in all_subtasks:
        tid = st.get("Task ID", "")
        subtasks_by_task.setdefault(tid, []).append(st)

    lines = [f"*Today — {_format_date(date.today().isoformat())}*\n"]
    for task in tasks_list:
        subtasks = subtasks_by_task.get(str(task["ID"]), [])
        lines.append(format_single_task(task, subtasks, all_tasks))
        lines.append("")
    return "\n".join(lines)


def get_all_pending_tasks() -> str:
    all_tasks = sheets.get_all_tasks()
    all_subtasks = sheets.get_all_subtasks()
    pending = [t for t in all_tasks if t.get("Done", "FALSE").upper() == "FALSE"]
    if not pending:
        return "No pending tasks 🎉"

    subtasks_by_task = {}
    for st in all_subtasks:
        tid = st.get("Task ID", "")
        subtasks_by_task.setdefault(tid, []).append(st)

    major_name = sheets.major_type_name()
    daily = [t for t in pending if t.get("Type", "") != major_name]
    major = [t for t in pending if t.get("Type", "") == major_name]

    lines = ["*All pending tasks*\n"]

    if major:
        lines.append("📌 MAJOR")
        for task in major:
            subtasks = subtasks_by_task.get(str(task["ID"]), [])
            lines.append(format_single_task(task, subtasks, all_tasks))
            lines.append("")

    if daily:
        lines.append("📋 DAY TO DAY")
        for task in daily:
            subtasks = subtasks_by_task.get(str(task["ID"]), [])
            lines.append(format_single_task(task, subtasks, all_tasks))
            lines.append("")

    return "\n".join(lines)


def get_task_detail_with_subtasks(task_id: int) -> dict | None:
    task = sheets.get_task_by_id(task_id)
    if not task:
        return None
    subtasks = sheets.get_subtasks_for(task_id)
    return {"task": task, "subtasks": subtasks}


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

def create_task(title: str, category: str, type_: str, date_str: str = "") -> dict:
    task_id = sheets.add_task(title, category, type_, date_str)
    return {
        "ID": str(task_id),
        "Title": title,
        "Category": category,
        "Type": type_,
        "Done": "FALSE",
        "Date": date_str,
        "Blocked By": "",
    }


def create_subtask(task_id: int, title: str) -> dict | None:
    parent = sheets.get_task_by_id(task_id)
    if not parent:
        return None
    subtask_id = sheets.add_subtask(task_id, title)
    return {
        "ID": str(subtask_id),
        "Task ID": str(task_id),
        "Title": title,
        "Done": "FALSE",
    }


# ---------------------------------------------------------------------------
# Complete
# ---------------------------------------------------------------------------

def complete_task(task_id: int) -> dict:
    subtasks = sheets.get_subtasks_for(task_id)
    pending_subtasks = [s for s in subtasks if s.get("Done", "FALSE").upper() == "FALSE"]
    if pending_subtasks:
        return {
            "status": "pending_subtasks",
            "subtasks": [s["Title"] for s in pending_subtasks],
            "message": f"⚠️ Task #{task_id} has pending subtasks.",
        }
    success = sheets.update_task_done(task_id, True)
    if not success:
        return {"status": "error", "message": f"Task #{task_id} not found."}
    return {"status": "done", "message": f"✅ Task #{task_id} marked as done!"}


def complete_task_force(task_id: int) -> dict:
    subtasks = sheets.get_subtasks_for(task_id)
    for st in subtasks:
        sheets.update_subtask_done(int(st["ID"]), True)
    success = sheets.update_task_done(task_id, True)
    if not success:
        return {"status": "error", "message": f"Task #{task_id} not found."}
    return {"status": "done", "message": f"✅ Task #{task_id} and all subtasks marked as done!"}


def complete_subtask(subtask_id: int) -> dict:
    success = sheets.update_subtask_done(subtask_id, True)
    if not success:
        return {"status": "error", "message": f"Subtask #{subtask_id} not found."}
    return {"status": "done", "message": f"✅ Subtask #{subtask_id} marked as done!"}


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

def get_types() -> list[str]:
    return sheets.get_types()


def get_categories() -> list[str]:
    return sheets.get_categories()