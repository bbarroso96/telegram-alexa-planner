from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from config.settings import config
from bot import tasks

# Conversation states
CHOOSING_CATEGORY, CHOOSING_TYPE, CHOOSING_DATE, TYPING_TITLE = range(4)
TYPING_SUBTASK_TITLE = 4


# ---------------------------------------------------------------------------
# Auth guard
# ---------------------------------------------------------------------------

def _is_allowed(update: Update) -> bool:
    return update.effective_user.id in config.allowed_user_ids


def _unauthorized() -> str:
    return "⛔ You are not authorized to use this bot."


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_allowed(update):
        await update.message.reply_text(_unauthorized())
        return
    await update.message.reply_text(
        "*Telegram Alexa Planner* 📋\n\n"
        "Here's what I can do:\n\n"
        "/add — add a new task\n"
        "/list — list all pending tasks\n"
        "/today — tasks scheduled for today\n"
        "/done <id> — mark a task as done\n"
        "/done <id> force — mark done even with pending subtasks\n"
        "/subtask <task\\_id> <title> — add a subtask\n"
        "/donesub <subtask\\_id> — mark a subtask as done\n"
        "/task <id> — view task detail\n"
        "/cancel — cancel current operation",
        parse_mode="Markdown",
    )


# ---------------------------------------------------------------------------
# /list
# ---------------------------------------------------------------------------

async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_allowed(update):
        await update.message.reply_text(_unauthorized())
        return
    text = tasks.get_all_pending_tasks()
    await update.message.reply_text(text, parse_mode="Markdown")


# ---------------------------------------------------------------------------
# /today
# ---------------------------------------------------------------------------

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_allowed(update):
        await update.message.reply_text(_unauthorized())
        return
    text = tasks.get_today_tasks()
    await update.message.reply_text(text, parse_mode="Markdown")


# ---------------------------------------------------------------------------
# /task <id>
# ---------------------------------------------------------------------------

async def task_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_allowed(update):
        await update.message.reply_text(_unauthorized())
        return
    if not context.args:
        await update.message.reply_text("Usage: /task <id>")
        return
    try:
        task_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Please provide a valid task ID.")
        return
    text = tasks.get_task_detail(task_id)
    await update.message.reply_text(text, parse_mode="Markdown")


# ---------------------------------------------------------------------------
# /done <id> [force]
# ---------------------------------------------------------------------------

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_allowed(update):
        await update.message.reply_text(_unauthorized())
        return
    if not context.args:
        await update.message.reply_text("Usage: /done <id> or /done <id> force")
        return
    try:
        task_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Please provide a valid task ID.")
        return

    force = len(context.args) > 1 and context.args[1].lower() == "force"
    if force:
        text = tasks.complete_task_force(task_id)
    else:
        text = tasks.complete_task(task_id)
    await update.message.reply_text(text, parse_mode="Markdown")


# ---------------------------------------------------------------------------
# /donesub <subtask_id>
# ---------------------------------------------------------------------------

async def done_subtask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_allowed(update):
        await update.message.reply_text(_unauthorized())
        return
    if not context.args:
        await update.message.reply_text("Usage: /donesub <subtask_id>")
        return
    try:
        subtask_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Please provide a valid subtask ID.")
        return
    text = tasks.complete_subtask(subtask_id)
    await update.message.reply_text(text)


# ---------------------------------------------------------------------------
# /subtask <task_id> <title>
# ---------------------------------------------------------------------------

async def add_subtask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_allowed(update):
        await update.message.reply_text(_unauthorized())
        return
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Usage: /subtask <task_id> <title>")
        return
    try:
        task_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Please provide a valid task ID.")
        return

    title = " ".join(context.args[1:])
    subtask = tasks.create_subtask(task_id, title)
    if not subtask:
        await update.message.reply_text(f"Task #{task_id} not found.")
        return
    await update.message.reply_text(
        f"✅ Subtask added to task #{task_id}:\n_{title}_",
        parse_mode="Markdown",
    )


# ---------------------------------------------------------------------------
# /add — conversation handler
# ---------------------------------------------------------------------------

async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _is_allowed(update):
        await update.message.reply_text(_unauthorized())
        return ConversationHandler.END

    await update.message.reply_text("What's the task title?")
    return TYPING_TITLE


async def received_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["title"] = update.message.text.strip()

    categories = tasks.get_categories()
    keyboard = [[InlineKeyboardButton(c, callback_data=f"cat:{c}")] for c in categories]
    await update.message.reply_text(
        "Choose a category:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return CHOOSING_CATEGORY


async def received_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["category"] = query.data.split(":", 1)[1]

    types_ = tasks.get_types()
    keyboard = [[InlineKeyboardButton(t.capitalize(), callback_data=f"type:{t}")] for t in types_]
    await query.edit_message_text(
        "Choose a type:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return CHOOSING_TYPE


async def received_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["type"] = query.data.split(":", 1)[1]

    keyboard = [
        [InlineKeyboardButton("Today", callback_data="date:today")],
        [InlineKeyboardButton("Tomorrow", callback_data="date:tomorrow")],
        [InlineKeyboardButton("Enter a date", callback_data="date:custom")],
        [InlineKeyboardButton("No date (open task)", callback_data="date:none")],
    ]
    await query.edit_message_text(
        "When do you plan to work on this?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return CHOOSING_DATE


async def received_date_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    from datetime import date, timedelta
    query = update.callback_query
    await query.answer()
    choice = query.data.split(":", 1)[1]

    if choice == "today":
        context.user_data["date"] = date.today().isoformat()
        return await _finalize_task(query, context)
    elif choice == "tomorrow":
        context.user_data["date"] = (date.today() + timedelta(days=1)).isoformat()
        return await _finalize_task(query, context)
    elif choice == "none":
        context.user_data["date"] = ""
        return await _finalize_task(query, context)
    else:
        await query.edit_message_text("Enter the date (YYYY-MM-DD):")
        return CHOOSING_DATE


async def received_custom_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    raw = update.message.text.strip()
    try:
        from datetime import date
        date.fromisoformat(raw)
        context.user_data["date"] = raw
    except ValueError:
        await update.message.reply_text("Invalid date. Please use YYYY-MM-DD format:")
        return CHOOSING_DATE
    return await _finalize_task(update, context)


async def _finalize_task(update_or_query, context: ContextTypes.DEFAULT_TYPE) -> int:
    data = context.user_data
    task = tasks.create_task(
        title=data["title"],
        category=data["category"],
        type_=data["type"],
        date_str=data.get("date", ""),
    )
    date_display = task["Date"] if task["Date"] else "open"
    text = (
        f"✅ Task created!\n\n"
        f"*#{task['ID']} {task['Title']}*\n"
        f"🏷 {task['Category']}  |  {task['Type']}\n"
        f"📅 {date_display}"
    )
    if hasattr(update_or_query, "edit_message_text"):
        await update_or_query.edit_message_text(text, parse_mode="Markdown")
    else:
        await update_or_query.message.reply_text(text, parse_mode="Markdown")
    context.user_data.clear()
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# /cancel
# ---------------------------------------------------------------------------

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END
