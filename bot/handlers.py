from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from config.settings import config
from bot import tasks

# Conversation states
CHOOSING_CATEGORY, CHOOSING_TYPE, CHOOSING_DATE, TYPING_TITLE, CHOOSING_SUBTASK_TASK, TYPING_SUBTASK_TITLE = range(6)


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
        "/today — today's daily tasks\n"
        "/done — mark a task as done\n"
        "/taskdetail — view and manage a task\n"
        "/addsubtask — add a subtask to a task\n"
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
# /today — shows today's tasks with a ✅ button on each
# ---------------------------------------------------------------------------

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_allowed(update):
        await update.message.reply_text(_unauthorized())
        return

    task_list = tasks.get_today_task_list()
    if not task_list:
        await update.message.reply_text("No daily tasks for today 🎉")
        return

    from datetime import date
    await update.message.reply_text(f"*Daily tasks — {date.today().isoformat()}*", parse_mode="Markdown")

    for task in task_list:
        text = tasks.format_single_task(task)
        keyboard = [[InlineKeyboardButton("✅ Mark done", callback_data=f"done:{task['ID']}")]]
        await update.message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


# ---------------------------------------------------------------------------
# /done — shows pending tasks as buttons
# ---------------------------------------------------------------------------

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_allowed(update):
        await update.message.reply_text(_unauthorized())
        return

    pending = tasks.get_pending_task_list()
    if not pending:
        await update.message.reply_text("No pending tasks 🎉")
        return

    keyboard = [
        [InlineKeyboardButton(f"#{t['ID']} {t['Title']}", callback_data=f"done:{t['ID']}")]
        for t in pending
    ]
    await update.message.reply_text(
        "Which task did you complete?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_done_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    task_id = int(query.data.split(":")[1])

    result = tasks.complete_task(task_id)

    if result["status"] == "pending_subtasks":
        names = "\n".join(f"  ⬜ {s}" for s in result["subtasks"])
        keyboard = [
            [InlineKeyboardButton("✅ Force done", callback_data=f"forcedone:{task_id}")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_action")],
        ]
        await query.edit_message_text(
            f"⚠️ Task #{task_id} has pending subtasks:\n{names}\n\nForce complete anyway?",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    else:
        await query.edit_message_text(result["message"])


async def handle_force_done_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    task_id = int(query.data.split(":")[1])
    result = tasks.complete_task_force(task_id)
    await query.edit_message_text(result["message"])


# ---------------------------------------------------------------------------
# /taskdetail — shows all tasks as buttons, then full detail with actions
# ---------------------------------------------------------------------------

async def task_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_allowed(update):
        await update.message.reply_text(_unauthorized())
        return

    all_tasks = tasks.get_pending_task_list()
    if not all_tasks:
        await update.message.reply_text("No pending tasks.")
        return

    keyboard = [
        [InlineKeyboardButton(f"#{t['ID']} {t['Title']}", callback_data=f"detail:{t['ID']}")]
        for t in all_tasks
    ]
    await update.message.reply_text(
        "Which task do you want to see?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_detail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    task_id = int(query.data.split(":")[1])

    detail = tasks.get_task_detail_with_subtasks(task_id)
    if not detail:
        await query.edit_message_text(f"Task #{task_id} not found.")
        return

    text = tasks.format_single_task(detail["task"], detail["subtasks"])

    buttons = []
    if detail["task"].get("Done", "FALSE").upper() == "FALSE":
        buttons.append(InlineKeyboardButton("✅ Mark done", callback_data=f"done:{task_id}"))

    keyboard = [buttons] if buttons else []

    for st in detail["subtasks"]:
        if st.get("Done", "FALSE").upper() == "FALSE":
            keyboard.append([
                InlineKeyboardButton(
                    f"✅ {st['Title']}",
                    callback_data=f"donesub:{st['ID']}",
                )
            ])

    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
    )


async def handle_donesub_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    subtask_id = int(query.data.split(":")[1])
    result = tasks.complete_subtask(subtask_id)
    await query.edit_message_text(result["message"])


async def handle_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Cancelled.")


# ---------------------------------------------------------------------------
# /addsubtask — conversation: pick task → type title
# ---------------------------------------------------------------------------

async def add_subtask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _is_allowed(update):
        await update.message.reply_text(_unauthorized())
        return ConversationHandler.END

    pending = tasks.get_pending_task_list()
    if not pending:
        await update.message.reply_text("No pending tasks to add a subtask to.")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton(t["Title"], callback_data=f"subtask_task:{t['ID']}")]
        for t in pending
    ]
    await update.message.reply_text(
        "Which task do you want to add a subtask to?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return CHOOSING_SUBTASK_TASK


async def received_subtask_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    task_id = int(query.data.split(":")[1])
    context.user_data["subtask_task_id"] = task_id

    task = tasks.get_task_detail_with_subtasks(task_id)
    task_title = task["task"]["Title"] if task else f"#{task_id}"

    await query.edit_message_text(f"Adding subtask to *{task_title}*\n\nWhat's the subtask title?", parse_mode="Markdown")
    return TYPING_SUBTASK_TITLE


async def received_subtask_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    title = update.message.text.strip()
    task_id = context.user_data.get("subtask_task_id")

    subtask = tasks.create_subtask(task_id, title)
    if not subtask:
        await update.message.reply_text("Something went wrong. Task not found.")
        return ConversationHandler.END

    task = tasks.get_task_detail_with_subtasks(task_id)
    task_title = task["task"]["Title"] if task else f"#{task_id}"

    await update.message.reply_text(
        f"✅ Subtask added to *{task_title}*:\n_{title}_",
        parse_mode="Markdown",
    )
    context.user_data.clear()
    return ConversationHandler.END


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
    keyboard = [[InlineKeyboardButton(t, callback_data=f"type:{t}")] for t in types_]
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
        "When do you plan to start working on this?",
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