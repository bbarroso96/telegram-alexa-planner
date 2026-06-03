import gspread
from google.oauth2.service_account import Credentials
from config.settings import config

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _get_client() -> gspread.Client:
    creds = Credentials.from_service_account_info(config.google_creds, scopes=SCOPES)
    return gspread.authorize(creds)


def _get_sheet(tab: str) -> gspread.Worksheet:
    client = _get_client()
    spreadsheet = client.open_by_key(config.spreadsheet_id)
    return spreadsheet.worksheet(tab)


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

def get_types() -> list[str]:
    sheet = _get_sheet("Types")
    return [row[0] for row in sheet.get_all_values()[1:] if row and row[0]]


def get_categories() -> list[str]:
    sheet = _get_sheet("Categories")
    return [row[0] for row in sheet.get_all_values()[1:] if row and row[0]]


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

def get_all_tasks() -> list[dict]:
    sheet = _get_sheet("Tasks")
    rows = sheet.get_all_values()
    if len(rows) < 2:
        return []
    headers = rows[0]
    return [dict(zip(headers, row)) for row in rows[1:] if any(row)]


def get_task_by_id(task_id: int) -> dict | None:
    tasks = get_all_tasks()
    for task in tasks:
        if task.get("ID") == str(task_id):
            return task
    return None


def get_next_task_id() -> int:
    tasks = get_all_tasks()
    if not tasks:
        return 1
    ids = [int(t["ID"]) for t in tasks if t.get("ID", "").isdigit()]
    return max(ids) + 1 if ids else 1


def append_task(task: dict) -> None:
    sheet = _get_sheet("Tasks")
    sheet.append_row([
        task["ID"],
        task["Title"],
        task["Category"],
        task["Type"],
        task["Done"],
        task.get("Date", ""),
        task.get("Blocked By", ""),
    ])


def update_task_done(task_id: int, done: bool) -> bool:
    sheet = _get_sheet("Tasks")
    rows = sheet.get_all_values()
    for i, row in enumerate(rows[1:], start=2):
        if row[0] == str(task_id):
            sheet.update_cell(i, 5, str(done).upper())
            return True
    return False


# ---------------------------------------------------------------------------
# Subtasks
# ---------------------------------------------------------------------------

def get_all_subtasks() -> list[dict]:
    sheet = _get_sheet("Subtasks")
    rows = sheet.get_all_values()
    if len(rows) < 2:
        return []
    headers = rows[0]
    return [dict(zip(headers, row)) for row in rows[1:] if any(row)]


def get_subtasks_for(task_id: int) -> list[dict]:
    return [s for s in get_all_subtasks() if s.get("Task ID") == str(task_id)]


def get_next_subtask_id() -> int:
    sheet = _get_sheet("Subtasks")
    rows = sheet.get_all_values()
    if len(rows) < 2:
        return 1
    ids = [int(r[0]) for r in rows[1:] if r and r[0].isdigit()]
    return max(ids) + 1 if ids else 1


def append_subtask(subtask: dict) -> None:
    sheet = _get_sheet("Subtasks")
    sheet.append_row([
        subtask["ID"],
        subtask["Task ID"],
        subtask["Title"],
        subtask["Done"],
    ])


def update_subtask_done(subtask_id: int, done: bool) -> bool:
    sheet = _get_sheet("Subtasks")
    rows = sheet.get_all_values()
    for i, row in enumerate(rows[1:], start=2):
        if row[0] == str(subtask_id):
            sheet.update_cell(i, 4, str(done).upper())
            return True
    return False