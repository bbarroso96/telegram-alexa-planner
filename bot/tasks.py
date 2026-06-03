from datetime import date
from bot import sheets


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


def _format_task(task: dict, all_tasks: list[dict], subtasks: list[dict] | None = None) -> str:
    blocked = _task_is_blocked(task, all_tasks)
    done = task.get("Done", "FALSE").upper() == "TRUE"

    status = "✅" if done else ("🔒" if blocked else "⬜")
    date_str = f"  📅 {task['Date']}" if task.get("Date") else "  📅 open"
    blocker_ids = _parse_blocked_by(task.get("Blocked By", ""))
    blocked_str = f"  🚧 blocked by: {', '.join(f'#{b}' for b in blocker_ids)}" if blocker_ids else ""

    lines = [
        f"{status} #{task['ID']} *{task['Title']}*",
        f"  🏷 {task.get('Category', '')}  |  {task.get('Type', '')}",
        date_str,
    ]
    if blocked_str:
        lines.append(blocked_str)

    if subtasks:
        for st in subtasks:
            st_done = st.get("Done", "FALSE").upper() == "TRUE"
            st_status = "✅" if st_done else "⬜"
            lines.append(f"    {st_status} {st['Title']}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

def get_today_tasks() -> str:
    today_str = date.today().isoformat()
    all_tasks = sheets.get_all_tasks()
    tasks = [
        t for t in all_tasks
        if t.get("Date") == today_str and t.get("Done", "FALSE").upper() == "FALSE"
    ]
    if not tasks:
        return "No tasks scheduled for today 🎉"

    lines = [f"*Tasks for today — {today_str}*\n"]
    for task in tasks:
        subtasks = sheets.get_subtasks_for(int(task["ID"]))
        lines.append(_format_task(task, all_tasks, subtasks))
        lines.append("")
    return "\n".join(lines)


def get_all_pending_tasks() -> str:
    all_tasks = sheets.get_all_tasks()
    pending = [t for t in all_tasks if t.get("Done", "FALSE").upper() == "FALSE"]
    if not pending:
        return "No pending tasks 🎉"

    daily = [t for t in pending if t.get("Type", "").lower() == "daily"]
    major = [t for t in pending if t.get("Type", "").lower() == "major"]

    lines = ["*All pending tasks*\n"]

    if major:
        lines.append("🗂 *Major*")
        for task in major:
            subtasks = sheets.get_subtasks_for(int(task["ID"]))
            lines.append(_format_task(task, all_tasks, subtasks))
            lines.append("")

    if daily:
        lines.append("📋 *Daily*")
        for task in daily:
            subtasks = sheets.get_subtasks_for(int(task["ID"]))
            lines.append(_format_task(task, all_tasks, subtasks))
            lines.append("")

    return "\n".join(lines)


def get_task_detail(task_id: int) -> str:
    all_tasks = sheets.get_all_tasks()
    task = sheets.get_task_by_id(task_id)
    if not task:
        return f"Task #{task_id} not found."
    subtasks = sheets.get_subtasks_for(task_id)
    return _format_task(task, all_tasks, subtasks)


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

def create_task(title: str, category: str, type_: str, date_str: str = "") -> dict:
    task_id = sheets.get_next_task_id()
    task = {
        "ID": task_id,
        "Title": title,
        "Category": category,
        "Type": type_,
        "Done": "FALSE",
        "Date": date_str,
        "Blocked By": "",
    }
    sheets.append_task(task)
    return task


def create_subtask(task_id: int, title: str) -> dict | None:
    parent = sheets.get_task_by_id(task_id)
    if not parent:
        return None
    subtask_id = sheets.get_next_subtask_id()
    subtask = {
        "ID": subtask_id,
        "Task ID": task_id,
        "Title": title,
        "Done": "FALSE",
    }
    sheets.append_subtask(subtask)
    return subtask


# ---------------------------------------------------------------------------
# Complete
# ---------------------------------------------------------------------------

def complete_task(task_id: int) -> str:
    subtasks = sheets.get_subtasks_for(task_id)
    pending_subtasks = [s for s in subtasks if s.get("Done", "FALSE").upper() == "FALSE"]
    if pending_subtasks:
        names = ", ".join(s["Title"] for s in pending_subtasks)
        return f"⚠️ Task #{task_id} still has pending subtasks:\n{names}\n\nComplete them first or force done with /done {task_id} force"

    success = sheets.update_task_done(task_id, True)
    if not success:
        return f"Task #{task_id} not found."
    return f"✅ Task #{task_id} marked as done!"


def complete_task_force(task_id: int) -> str:
    subtasks = sheets.get_subtasks_for(task_id)
    for st in subtasks:
        sheets.update_subtask_done(int(st["ID"]), True)
    success = sheets.update_task_done(task_id, True)
    if not success:
        return f"Task #{task_id} not found."
    return f"✅ Task #{task_id} and all its subtasks marked as done!"


def complete_subtask(subtask_id: int) -> str:
    success = sheets.update_subtask_done(subtask_id, True)
    if not success:
        return f"Subtask #{subtask_id} not found."
    return f"✅ Subtask #{subtask_id} marked as done!"


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

def get_types() -> list[str]:
    return sheets.get_types()


def get_categories() -> list[str]:
    return sheets.get_categories()
