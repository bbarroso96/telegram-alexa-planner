from datetime import date, timedelta
from core import repository as sheets
from alexa import apl


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


FOLLOW_UP = "Is there anything else I can help with?"

def _ssml(text: str, keep_open: bool = True) -> dict:
    return {
        "version": "1.0",
        "response": {
            "outputSpeech": {
                "type": "SSML",
                "ssml": f"<speak>{text}{' ' + FOLLOW_UP if keep_open else ''}</speak>",
            },
            "shouldEndSession": not keep_open,
        },
    }


def _ssml_keep_open(text: str) -> dict:
    return _ssml(text, keep_open=True)


def _ssml_close(text: str) -> dict:
    return _ssml(text, keep_open=False)


# ---------------------------------------------------------------------------
# GetTodayTasksIntent
# ---------------------------------------------------------------------------

def get_today_speech() -> str:
    today_str = _get_today_str()
    major_name = sheets.major_type_name()
    all_tasks = sheets.get_all_tasks()
    tasks = [
        t for t in all_tasks
        if t.get("Done", "FALSE").upper() == "FALSE"
        and t.get("Type", "") != major_name
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
        type_=sheets.type_name_for_kind("d2d"),   # role lookup — survives type renames
        date_str=_get_today_str(),
    )
    return f"Added: {task['Title']}."


# ---------------------------------------------------------------------------
# MarkTaskDoneIntent — multi-turn
# ---------------------------------------------------------------------------

def start_mark_done_speech() -> dict:
    return {
        "version": "1.0",
        "response": {
            "outputSpeech": {
                "type": "SSML",
                "ssml": "<speak>Which task did you complete?</speak>",
            },
            "directives": [
                {
                    "type": "Dialog.ElicitSlot",
                    "slotToElicit": "taskName",
                    "updatedIntent": {
                        "name": "MarkTaskDoneIntent",
                        "confirmationStatus": "NONE",
                        "slots": {
                            "taskName": {
                                "name": "taskName",
                                "confirmationStatus": "NONE"
                            }
                        }
                    }
                }
            ],
            "shouldEndSession": False,
        },
    }


def mark_task_done_speech(task_name: str) -> dict:
    task = _find_task_by_name(task_name)
    if not task:
        return {
            "version": "1.0",
            "response": {
                "outputSpeech": {
                    "type": "SSML",
                    "ssml": f"<speak>I couldn't find a task called {task_name}. Which task did you complete?</speak>",
                },
                "directives": [
                    {
                        "type": "Dialog.ElicitSlot",
                        "slotToElicit": "taskName",
                        "updatedIntent": {
                            "name": "MarkTaskDoneIntent",
                            "confirmationStatus": "NONE",
                            "slots": {
                                "taskName": {
                                    "name": "taskName",
                                    "confirmationStatus": "NONE"
                                }
                            }
                        }
                    }
                ],
                "shouldEndSession": False,
            },
        }

    sheets.update_task_done(int(task["ID"]), True)
    return _ssml_keep_open(f"Done! Marked {task['Title']} as complete. Any more tasks to mark done?")


# ---------------------------------------------------------------------------
# GetAllTasksIntent / GetMajorTasksIntent
# ---------------------------------------------------------------------------

def _list_speech(titles: list[str], empty: str, noun: str) -> str:
    if not titles:
        return empty
    if len(titles) == 1:
        return f"You have 1 {noun}: {titles[0]}."
    joined = ", ".join(titles[:-1]) + f", and {titles[-1]}"
    return f"You have {len(titles)} {noun}s: {joined}."


def get_all_tasks_speech() -> str:
    pending = [t for t in sheets.get_all_tasks() if t.get("Done", "FALSE").upper() == "FALSE"]
    return _list_speech([t["Title"] for t in pending],
                        "You have no pending tasks. All clear!", "pending task")


def get_major_tasks_speech() -> str:
    major_name = sheets.major_type_name()
    majors = [t for t in sheets.get_all_tasks()
              if t.get("Done", "FALSE").upper() == "FALSE" and t.get("Type", "") == major_name]
    return _list_speech([t["Title"] for t in majors],
                        "You have no major tasks right now.", "major task")


# ---------------------------------------------------------------------------
# GetEventsTodayIntent / GetUpcomingEventsIntent
# ---------------------------------------------------------------------------

def get_events_today_speech() -> str:
    today = _get_today_str()
    titles = [e["title"] for e in sheets.get_all_events() if e["start"] <= today <= e["end"]]
    if not titles:
        return "You have nothing on your calendar today."
    if len(titles) == 1:
        return f"Today you have: {titles[0]}."
    joined = ", ".join(titles[:-1]) + f", and {titles[-1]}"
    return f"Today you have {len(titles)} events: {joined}."


def get_upcoming_events_speech() -> str:
    today = date.today()
    today_s, horizon = today.isoformat(), (today + timedelta(days=7)).isoformat()
    upcoming = sorted(
        (e for e in sheets.get_all_events() if e["start"] <= horizon and e["end"] >= today_s),
        key=lambda e: e["start"],
    )
    titles = [e["title"] for e in upcoming]
    if not titles:
        return "You have nothing coming up in the next week."
    if len(titles) == 1:
        return f"Coming up this week: {titles[0]}."
    joined = ", ".join(titles[:-1]) + f", and {titles[-1]}"
    return f"Coming up this week you have {len(titles)} events: {joined}."


# ---------------------------------------------------------------------------
# Screen (APL) — build display item lists + attach a RenderDocument directive
# ---------------------------------------------------------------------------

def _pretty_today() -> str:
    return apl.short_date(_get_today_str()).upper()


def _done_ids(all_tasks) -> set:
    return {int(t["ID"]) for t in all_tasks
            if t.get("Done", "").upper() == "TRUE" and t.get("ID", "").isdigit()}


def _is_blocked(task, done_ids) -> bool:
    bids = [int(x) for x in task.get("Blocked By", "").split(",") if x.strip().isdigit()]
    return any(b not in done_ids for b in bids)


def _task_item(task, done_ids) -> dict:
    done = task.get("Done", "FALSE").upper() == "TRUE"
    marker = "[x]" if done else ("!!" if _is_blocked(task, done_ids) else "▸")
    return {"marker": marker, "title": task["Title"], "meta": task.get("Category", ""), "dim": done}


def _event_item(e) -> dict:
    meta = apl.short_date(e["start"]) if e["single"] else \
        apl.short_date(e["start"]) + "–" + apl.short_date(e["end"])
    return {"marker": "◆", "title": e["title"], "meta": meta}


def _today_items() -> list:
    today = _get_today_str()
    all_tasks = sheets.get_all_tasks()
    done_ids = _done_ids(all_tasks)
    major = sheets.major_type_name()
    rows = [t for t in all_tasks if t.get("Done", "FALSE").upper() == "FALSE"
            and t.get("Type", "") != major and (not t.get("Date") or t.get("Date") <= today)]
    return [_task_item(t, done_ids) for t in rows]


def _pending_items(major_only=False) -> list:
    all_tasks = sheets.get_all_tasks()
    done_ids = _done_ids(all_tasks)
    major = sheets.major_type_name()
    rows = [t for t in all_tasks if t.get("Done", "FALSE").upper() == "FALSE"
            and (not major_only or t.get("Type", "") == major)]
    return [_task_item(t, done_ids) for t in rows]


def _blocked_items() -> list:
    all_tasks = sheets.get_all_tasks()
    done_ids = _done_ids(all_tasks)
    return [_task_item(t, done_ids) for t in all_tasks
            if t.get("Done", "FALSE").upper() == "FALSE" and _is_blocked(t, done_ids)]


def _events_today_items() -> list:
    today = _get_today_str()
    return [_event_item(e) for e in sheets.get_all_events() if e["start"] <= today <= e["end"]]


def _upcoming_items() -> list:
    today = date.today()
    today_s, horizon = today.isoformat(), (today + timedelta(days=7)).isoformat()
    evs = sorted((e for e in sheets.get_all_events()
                  if e["start"] <= horizon and e["end"] >= today_s), key=lambda e: e["start"])
    return [_event_item(e) for e in evs]


def _render(speech: str, title: str, items: list, supports_apl: bool) -> dict:
    resp = _ssml_keep_open(speech)
    if supports_apl:
        resp["response"]["directives"] = [{
            "type": "Alexa.Presentation.APL.RenderDocument",
            "token": "directives",
            "document": apl.document(title, items),
        }]
    return resp


def launch_response(supports_apl: bool) -> dict:
    speech = ("Welcome to your planner. You can ask what's planned for today, "
              "what's blocked, or what's coming up this week.")
    return _render(speech, "TODAY · " + _pretty_today(), _today_items(), supports_apl)


# ---------------------------------------------------------------------------
# Intent router
# ---------------------------------------------------------------------------

def handle_intent(intent_name: str, slots: dict, session_attributes: dict,
                  supports_apl: bool = False) -> dict:
    if intent_name == "GetTodayTasksIntent":
        return _render(get_today_speech(), "TODAY · " + _pretty_today(), _today_items(), supports_apl)

    elif intent_name == "GetBlockedTasksIntent":
        return _render(get_blocked_speech(), "BLOCKED", _blocked_items(), supports_apl)

    elif intent_name == "GetAllTasksIntent":
        return _render(get_all_tasks_speech(), "ALL TASKS", _pending_items(), supports_apl)

    elif intent_name == "GetMajorTasksIntent":
        return _render(get_major_tasks_speech(), sheets.major_type_name().upper(),
                       _pending_items(major_only=True), supports_apl)

    elif intent_name == "GetEventsTodayIntent":
        return _render(get_events_today_speech(), "EVENTS · TODAY", _events_today_items(), supports_apl)

    elif intent_name == "GetUpcomingEventsIntent":
        return _render(get_upcoming_events_speech(), "THIS WEEK", _upcoming_items(), supports_apl)

    elif intent_name == "AddQuickTaskIntent":
        task_name = slots.get("taskName", {}).get("value", "")
        if not task_name:
            return _ssml_keep_open("Sorry, I didn't catch the task name. What would you like to add?")
        return _ssml_keep_open(add_quick_task_speech(task_name))

    elif intent_name == "MarkTaskDoneIntent":
        task_name = slots.get("taskName", {}).get("value", "")
        if not task_name:
            return start_mark_done_speech()
        return mark_task_done_speech(task_name)

    elif intent_name == "MoreTasksDoneIntent":
        return start_mark_done_speech()

    elif intent_name in ("AMAZON.NoIntent", "AMAZON.StopIntent", "AMAZON.CancelIntent"):
        return _ssml_close("Goodbye!")

    elif intent_name == "AMAZON.HelpIntent":
        return _ssml_keep_open(
            "You can ask me what you have today, what all your tasks are, "
            "what your major tasks are, what's blocked, what's on your calendar "
            "today, or what's coming up this week. You can also add a task or "
            "mark tasks as done."
        )

    return _ssml_keep_open("Sorry, I didn't understand that. What can I help you with?")