from datetime import date
from bot import sheets


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_today_str() -> str:
    return date.today().isoformat()


def _find_task_by_name(name: str) -> dict | None:
    all_tasks = sheets.get_all_tasks()
    name_lower = name.lower().strip()
    # Exact match first
    for task in all_tasks:
        if task.get("Title", "").lower() == name_lower:
            return task
    # Partial match fallback
    for task in all_tasks:
        if name_lower in task.get("Title", "").lower():
            return task
    return None


def _ssml(text: str) -> dict:
    return {
        "version": "1.0",
        "response": {
            "outputSpeech": {
                "type": "SSML",
                "ssml": f"<speak>{text}</speak>",
            },
            "shouldEndSession": True,
        },
    }


def _ssml_keep_open(text: str) -> dict:
    return {
        "version": "1.0",
        "response": {
            "outputSpeech": {
                "type": "SSML",
                "ssml": f"<speak>{text}</speak>",
            },
            "shouldEndSession": False,
        },
    }


# ---------------------------------------------------------------------------
# GetTodayTasksIntent
# ---------------------------------------------------------------------------

def get_today_speech() -> str:
    today_str = _get_today_str()
    all_tasks = sheets.get_all_tasks()
    tasks = [
        t for t in all_tasks
        if t.get("Done", "FALSE").upper() == "FALSE"
        and t.get("Type", "") != "Major"
        and (not t.get("Date") or t.get("Date") <= today_str)
    ]
    if not tasks:
        return "You have no tasks for today. Enjoy your day!"
    titles = [t["Title"] for t in tasks]
    if len(titles) == 1:
        return f"You have 1 task for today: {titles[0]}."
    task_list = ", ".join(titles[:-1]) + f", and {titles[-1]}"
    return f"You have {len(titles)} tasks for today: {task_list}."


# ---------------------------------------------------------------------------
# GetBlockedTasksIntent
# ---------------------------------------------------------------------------

def get_blocked_speech() -> str:
    all_tasks = sheets.get_all_tasks()
    pending = [t for t in all_tasks if t.get("Done", "FALSE").upper() == "FALSE"]
    done_ids = {int(t["ID"]) for t in all_tasks if t.get("Done", "").upper() == "TRUE" and t.get("ID", "").isdigit()}

    blocked = []
    for task in pending:
        raw = task.get("Blocked By", "")
        if not raw:
            continue
        blocker_ids = [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]
        if any(bid not in done_ids for bid in blocker_ids):
            blocked.append(task["Title"])

    if not blocked:
        return "No tasks are currently blocked. Everything is clear!"
    if len(blocked) == 1:
        return f"1 task is blocked: {blocked[0]}."
    task_list = ", ".join(blocked[:-1]) + f", and {blocked[-1]}"
    return f"{len(blocked)} tasks are blocked: {task_list}."


# ---------------------------------------------------------------------------
# AddQuickTaskIntent
# ---------------------------------------------------------------------------

def add_quick_task_speech(task_name: str) -> str:
    from bot import tasks
    task = tasks.create_task(
        title=task_name,
        category="",
        type_="Day to Day",
        date_str=_get_today_str(),
    )
    return f"Added: {task['Title']}."


# ---------------------------------------------------------------------------
# MarkTaskDoneIntent — multi-turn
# ---------------------------------------------------------------------------

def start_mark_done_speech() -> dict:
    return _ssml_keep_open("Sure! Which task did you complete?")


def mark_task_done_speech(task_name: str) -> dict:
    task = _find_task_by_name(task_name)
    if not task:
        return _ssml_keep_open(f"I couldn't find a task called {task_name}. Which task did you complete?")

    sheets.update_task_done(int(task["ID"]), True)
    return _ssml_keep_open(f"Done! Marked {task['Title']} as complete. Any more?")


def finish_mark_done_speech() -> dict:
    return _ssml("All done. Goodbye!")


# ---------------------------------------------------------------------------
# Intent router
# ---------------------------------------------------------------------------

def handle_intent(intent_name: str, slots: dict, session_attributes: dict) -> dict:
    if intent_name == "GetTodayTasksIntent":
        return _ssml(get_today_speech())

    elif intent_name == "GetBlockedTasksIntent":
        return _ssml(get_blocked_speech())

    elif intent_name == "AddQuickTaskIntent":
        task_name = slots.get("taskName", {}).get("value", "")
        if not task_name:
            return _ssml("Sorry, I didn't catch the task name.")
        return _ssml(add_quick_task_speech(task_name))

    elif intent_name == "MarkTaskDoneIntent":
        task_name = slots.get("taskName", {}).get("value", "")
        if not task_name:
            return start_mark_done_speech()
        return mark_task_done_speech(task_name)

    elif intent_name == "MoreTasksDoneIntent":
        return start_mark_done_speech()

    elif intent_name in ("AMAZON.NoIntent", "AMAZON.StopIntent", "AMAZON.CancelIntent"):
        return finish_mark_done_speech()

    elif intent_name == "AMAZON.HelpIntent":
        return _ssml(
            "You can ask me: what do I have today, what's blocked, "
            "add a task, or mark tasks as done."
        )

    return _ssml("Sorry, I didn't understand that.")