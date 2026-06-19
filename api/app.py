import os
from contextlib import asynccontextmanager
from datetime import date

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core.db import init_db
from core import repository as repo
from api import schemas


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Planner API", lifespan=lifespan)

# Vite dev server runs on a different port; allow it during local development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Type mapping — the UI works in stable roles ('major'/'d2d'); storage keeps the
# display names (e.g. 'Major'/'Day to Day') so the Telegram bot and Alexa stay
# consistent. The mapping is driven by types.kind so names can be renamed freely.
# ---------------------------------------------------------------------------

def _store_type(t: str) -> str:
    """UI sends a role ('major'/'d2d') -> store the current name for that role."""
    if t in ("major", "d2d"):
        return repo.type_name_for_kind(t)
    return t  # already a stored name


# ---------------------------------------------------------------------------
# Serialization — legacy-shaped repo dicts -> clean JSON matching the design's
# data model (dateKind/beginDate/openDate, derived blocked/waiting_on, threads).
# ---------------------------------------------------------------------------

def _parse_ids(raw: str) -> list[int]:
    return [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]


def _serialize_task(task: dict, subtasks: list[dict], done_ids: set[int],
                    id_to_title: dict[int, str], updates_by: dict,
                    kind_by_name: dict) -> dict:
    blocker_ids = _parse_ids(task.get("Blocked By", ""))
    active = [bid for bid in blocker_ids if bid not in done_ids]
    date_str = task.get("Date", "")
    open_date = (task.get("CreatedAt", "") or "")[:10]
    return {
        "id": int(task["ID"]),
        "title": task["Title"],
        "type": kind_by_name.get(task.get("Type", ""), "d2d"),
        "category": task.get("Category", ""),
        "done": task["Done"].upper() == "TRUE",
        "dateKind": "begin" if date_str else "open",
        "beginDate": date_str or None,
        "openDate": open_date,
        "blocked": bool(active),
        "blocked_by": blocker_ids,
        "waiting_on": [id_to_title.get(bid, f"#{bid}") for bid in active],
        "updates": updates_by.get(("task", int(task["ID"])), []),
        "subs": [
            {
                "id": int(s["ID"]),
                "title": s["Title"],
                "done": s["Done"].upper() == "TRUE",
                "updates": updates_by.get(("subtask", int(s["ID"])), []),
            }
            for s in subtasks
        ],
    }


def _updates_index() -> dict:
    idx: dict = {}
    for u in repo.get_all_updates():
        idx.setdefault((u["target_type"], u["target_id"]), []).append(
            {"id": u["id"], "ts": u["ts"], "text": u["text"]}
        )
    return idx


def _all_tasks_serialized(include_done: bool = True) -> list[dict]:
    tasks = repo.get_all_tasks()
    all_subs = repo.get_all_subtasks()
    subs_by_task: dict[str, list] = {}
    for s in all_subs:
        subs_by_task.setdefault(s["Task ID"], []).append(s)
    done_ids = {int(t["ID"]) for t in tasks if t["Done"].upper() == "TRUE"}
    id_to_title = {int(t["ID"]): t["Title"] for t in tasks}
    updates_by = _updates_index()
    kind_by_name = {ty["name"]: ty["kind"] for ty in repo.get_types_full()}
    out = []
    for t in tasks:
        if not include_done and t["Done"].upper() == "TRUE":
            continue
        out.append(_serialize_task(t, subs_by_task.get(t["ID"], []), done_ids,
                                   id_to_title, updates_by, kind_by_name))
    return out


def _serialize_events() -> list[dict]:
    updates_by = _updates_index()
    return [
        {**e, "comments": updates_by.get(("event", e["id"]), [])}
        for e in repo.get_all_events()
    ]


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"ok": True}


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@app.get("/api/tasks")
def list_tasks(include_done: bool = True):
    return _all_tasks_serialized(include_done)


@app.get("/api/today")
def today_tasks():
    """Visible "directives" today: open tasks always, begin tasks from beginDate forward."""
    today_str = date.today().isoformat()
    return [
        t for t in _all_tasks_serialized(include_done=True)
        if t["dateKind"] == "open" or (t["beginDate"] and t["beginDate"] <= today_str)
    ]


@app.post("/api/tasks", status_code=201)
def create_task(t: schemas.TaskIn):
    task_id = repo.add_task(t.title, t.category, _store_type(t.type), t.date)
    return {"id": task_id}


@app.patch("/api/tasks/{task_id}")
def edit_task(task_id: int, patch: schemas.TaskPatch):
    if not repo.get_task_by_id(task_id):
        raise HTTPException(404, "Task not found")
    repo.update_task(
        task_id,
        title=patch.title,
        category=patch.category,
        type_=_store_type(patch.type) if patch.type is not None else None,
        date_str=patch.date,
        blocked_by=patch.blocked_by,
    )
    return {"ok": True}


@app.post("/api/tasks/{task_id}/done")
def complete_task(task_id: int):
    if not repo.update_task_done(task_id, True):
        raise HTTPException(404, "Task not found")
    return {"ok": True}


@app.post("/api/tasks/{task_id}/reopen")
def reopen_task(task_id: int):
    if not repo.update_task_done(task_id, False):
        raise HTTPException(404, "Task not found")
    return {"ok": True}


@app.delete("/api/tasks/{task_id}")
def remove_task(task_id: int):
    if not repo.delete_task(task_id):
        raise HTTPException(404, "Task not found")
    return {"ok": True}


@app.post("/api/tasks/{task_id}/updates", status_code=201)
def log_task_update(task_id: int, u: schemas.UpdateIn):
    if not repo.get_task_by_id(task_id):
        raise HTTPException(404, "Task not found")
    return repo.add_update("task", task_id, u.text)


# ---------------------------------------------------------------------------
# Subtasks
# ---------------------------------------------------------------------------

@app.post("/api/tasks/{task_id}/subtasks", status_code=201)
def create_subtask(task_id: int, s: schemas.SubtaskIn):
    if not repo.get_task_by_id(task_id):
        raise HTTPException(404, "Task not found")
    return {"id": repo.add_subtask(task_id, s.title)}


@app.post("/api/subtasks/{subtask_id}/done")
def complete_subtask(subtask_id: int):
    if not repo.update_subtask_done(subtask_id, True):
        raise HTTPException(404, "Subtask not found")
    return {"ok": True}


@app.post("/api/subtasks/{subtask_id}/reopen")
def reopen_subtask(subtask_id: int):
    if not repo.update_subtask_done(subtask_id, False):
        raise HTTPException(404, "Subtask not found")
    return {"ok": True}


@app.delete("/api/subtasks/{subtask_id}")
def remove_subtask(subtask_id: int):
    if not repo.delete_subtask(subtask_id):
        raise HTTPException(404, "Subtask not found")
    return {"ok": True}


@app.post("/api/subtasks/{subtask_id}/updates", status_code=201)
def log_subtask_update(subtask_id: int, u: schemas.UpdateIn):
    return repo.add_update("subtask", subtask_id, u.text)


# ---------------------------------------------------------------------------
# Calendar events
# ---------------------------------------------------------------------------

@app.get("/api/events")
def list_events():
    return _serialize_events()


@app.post("/api/events", status_code=201)
def create_event(e: schemas.EventIn):
    end = e.start if e.single else (e.end or e.start)
    event_id = repo.add_event(e.title, e.single, e.start, end)
    if e.comment.strip():
        repo.add_update("event", event_id, e.comment.strip())
    return {"id": event_id}


@app.patch("/api/events/{event_id}")
def edit_event(event_id: int, patch: schemas.EventPatch):
    if not repo.get_event(event_id):
        raise HTTPException(404, "Event not found")
    repo.update_event(event_id, title=patch.title, single=patch.single,
                      start=patch.start, end=patch.end)
    return {"ok": True}


@app.delete("/api/events/{event_id}")
def remove_event(event_id: int):
    if not repo.delete_event(event_id):
        raise HTTPException(404, "Event not found")
    return {"ok": True}


@app.post("/api/events/{event_id}/comments", status_code=201)
def add_event_comment(event_id: int, u: schemas.UpdateIn):
    if not repo.get_event(event_id):
        raise HTTPException(404, "Event not found")
    return repo.add_update("event", event_id, u.text)


# ---------------------------------------------------------------------------
# Update threads — generic delete
# ---------------------------------------------------------------------------

@app.delete("/api/updates/{update_id}")
def remove_update(update_id: int):
    if not repo.delete_update(update_id):
        raise HTTPException(404, "Update not found")
    return {"ok": True}


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

@app.get("/api/types")
def get_types():
    return repo.get_types_full()   # [{name, kind}], major role first


@app.post("/api/types", status_code=201)
def add_type(n: schemas.NameIn):
    repo.add_type(n.name)          # new types default to the 'd2d' role
    return {"ok": True}


@app.put("/api/types")
def rename_type(r: schemas.RenameIn):
    repo.rename_type(r.old, r.new)  # keeps role, cascades to tasks/bot/Alexa
    return {"ok": True}


@app.delete("/api/types")
def remove_type(name: str):   # ?name=... — query param handles spaces/slashes safely
    repo.delete_type(name)
    return {"ok": True}


@app.get("/api/categories")
def get_categories():
    return repo.get_categories()


@app.post("/api/categories", status_code=201)
def add_category(n: schemas.NameIn):
    repo.add_category(n.name)
    return {"ok": True}


@app.put("/api/categories")
def rename_category(r: schemas.RenameIn):
    repo.rename_category(r.old, r.new)   # cascades to tasks
    return {"ok": True}


@app.delete("/api/categories")
def remove_category(name: str):   # ?name=... — query param handles names with slashes/spaces
    repo.delete_category(name)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Serve the built frontend (when it exists)
# ---------------------------------------------------------------------------
_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(_DIST):
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="static")
