# telegram-alexa-planner

A personal task planner with multiple front-ends sharing one **SQLite** backend
(migrated off Google Sheets):
- **Telegram bot** (`python-telegram-bot` 21.6, long-polling) — rich interactive task management.
- **Alexa skill** (FastAPI, port 8001) — voice queries and quick actions.
- **REST API** (`api/app.py`) — backs the website / reTerminal front-ends.

This is a **separate project** from `telegram-expense-tracker` (sibling folder, own git repo
`github.com/bbarroso96/telegram-alexa-planner`). Keep secrets, deploys, and git operations scoped
to this folder.

## Running

```bash
.venv/Scripts/python.exe main.py
```

`main()` starts the Alexa uvicorn server in a daemon thread (port 8001), then runs Telegram
polling in the main thread.

⚠️ **Only one Telegram poller per bot token.** The bot is deployed on the Pi via systemd. Running
`main.py` locally while the Pi service is up causes Telegram `Conflict` errors — stop the Pi
service first, or for Alexa-only work run just `alexa.server:app` with uvicorn.

Run just the REST API (for website dev): `.venv/Scripts/python.exe -m uvicorn api.app:app --reload`.

- venv: `.venv` (Python 3.13 locally, though `.python-version` pins 3.11).
- Config comes from `.env` (gitignored): `BOT_TOKEN`, `ALLOWED_USER_IDS` (comma-separated ints),
  `DB_PATH` (default `data/planner.db`). `SPREADSHEET_ID` + `GOOGLE_CREDS_JSON` are only needed to
  re-run the one-time Sheets migration.
- **First-time DB setup**: `python -m scripts.migrate_from_sheets` (brings existing Sheets data in),
  or `python -m core.seed` for a fresh empty DB with starter types/categories.

## Architecture

```
main.py            # wires bot + Alexa; init_db() on startup; defines Telegram handlers
config/settings.py # Config dataclass from env (db_path, bot_token, allowed ids; Sheets fields optional)
core/
  db.py            # SQLite connection (WAL) + schema + init_db()
  repository.py    # data layer — returns legacy-shaped dicts; drop-in for the old bot.sheets
  seed.py          # `python -m core.seed` — starter types/categories for a fresh DB
bot/
  handlers.py      # Telegram command + conversation + callback handlers
  tasks.py         # business logic (queries, create, complete) — imports core.repository as `sheets`
  sheets.py        # OLD gspread layer — now used ONLY by the migration script
alexa/
  server.py        # FastAPI /alexa endpoint; routes Launch/Intent/SessionEnded
  intents.py       # per-intent speech builders + router — imports core.repository as `sheets`
api/
  app.py           # REST API for the website/reTerminal (tasks, subtasks, events, updates, types, categories)
  schemas.py       # pydantic request models
scripts/
  migrate_from_sheets.py  # one-time `python -m scripts.migrate_from_sheets [--reset]`
frontend/          # React 18 + Vite — the "DIRECTIVES" retro-CRT task list + calendar
  src/api.js       # fetch wrappers over /api
  src/App.jsx      # tabs, command bar, filters, sections (exports prettyDate)
  src/components/TaskRow.jsx   # task block: subtask tree, blocker-picker, update threads, inline edit
  src/components/Calendar.jsx  # month grid, event form, selected-day panel
```

### Website (frontend)
Built from a Claude design handoff (retro phosphor-green CRT terminal). Talks to the REST API.
- Dev: run the API (`uvicorn api.app:app --port 8000`) AND `cd frontend && npm run dev` (Vite :5173,
  proxies `/api` → :8000).
- Prod: `cd frontend && npm run build`; FastAPI auto-serves `frontend/dist` at `/` when it exists.
- Two tabs: **DIRECTIVES** (today view — open tasks always, begin tasks from their date) and **CALENDAR**
  (events + begin-task chips + a `TASKS (n)` chip on today). "Blocked" uses the **dependency** model
  (pick blocker tasks; `blocked`/`waiting_on` are derived) — consistent with the bot/Alexa. Tasks,
  subtasks and events each have threaded update/comment logs. Editing is supported (PATCH).

`core/repository.py` is the single storage module; `bot/tasks.py`, `alexa/intents.py`, and
`api/app.py` all go through it. Its **read functions return the same dict shape the old Sheets
layer did** (`"ID"`, `"Done": "TRUE"/"FALSE"`, etc.) so the bot/Alexa code was a near drop-in swap.
The REST API (`api/app.py`) re-serializes those into clean JSON (`id` int, `done` bool, nested
`subtasks`, derived `blocked`/`waiting_on`).

## Data model (SQLite — `data/planner.db`, gitignored)

- **tasks**: `id (AUTOINCREMENT), title, category, type, done (0/1), date, blocked_by, created_at`
  - `date` is `YYYY-MM-DD` or `''` (empty = "open", always shows).
  - `type` of `"Major"` is excluded from today/daily views.
  - `blocked_by` is a comma-separated list of blocker task ids; a task is blocked while any
    blocker is not done.
- **subtasks**: `id, task_id (FK, cascade delete), title, done`. A task can't be marked done
  while it has pending subtasks (unless force-completed).
- **types**: `name PRIMARY KEY, position, kind` — `kind` is a stable role (`major`/`d2d`) that
  survives renames. The bot/Alexa/web key off `kind` (via `repo.major_type_name()` and the API's
  kind mapping), NOT the literal name, so a type can be renamed and it cascades everywhere.
- **categories**: `name PRIMARY KEY, position`. Renaming cascades to `tasks.category`.

IDs are now DB `AUTOINCREMENT` (fixes the old `max+1` race between the two front-ends). The
migration script preserves original ids so `blocked_by` references stay valid.

## Alexa intents (`alexa/intents.py`)

- `GetTodayTasksIntent` — non-Major, undone, due today-or-earlier/open.
- `GetBlockedTasksIntent` — pending tasks with an unfinished blocker.
- `AddQuickTaskIntent` (slot `taskName`) — creates a "Day to Day" task dated today.
- `MarkTaskDoneIntent` (slot `taskName`) — multi-turn via `Dialog.ElicitSlot`; matches task by
  exact-then-partial title.
- `MoreTasksDoneIntent` — re-prompts the mark-done flow.
- Sessions are kept open (`shouldEndSession: False`) with a follow-up prompt between intents.

## Notes

- Migrated off Google Sheets to SQLite (see `scripts/migrate_from_sheets.py`). The old
  `bot/sheets.py` gspread layer is retained only for that one-time migration.
