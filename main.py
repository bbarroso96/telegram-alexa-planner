from dotenv import load_dotenv
load_dotenv()

import threading
import uvicorn
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, filters,
)
from config.settings import config
from bot.handlers import (
    start, add_task, list_tasks, today, done, add_subtask, task_detail, cancel,
    received_title, received_category, received_type,
    received_date_choice, received_custom_date,
    received_subtask_task, received_subtask_title,
    handle_done_callback, handle_force_done_callback,
    handle_detail_callback, handle_donesub_callback, handle_cancel_callback,
    TYPING_TITLE, CHOOSING_CATEGORY, CHOOSING_TYPE, CHOOSING_DATE,
    CHOOSING_SUBTASK_TASK, TYPING_SUBTASK_TITLE,
)
from alexa.server import app as alexa_app


def run_alexa_server():
    uvicorn.run(alexa_app, host="0.0.0.0", port=8001, log_level="warning")


def run_telegram_bot():
    app = ApplicationBuilder().token(config.bot_token).build()

    add_conv = ConversationHandler(
        entry_points=[CommandHandler("add", add_task)],
        states={
            TYPING_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_title)],
            CHOOSING_CATEGORY: [CallbackQueryHandler(received_category, pattern="^cat:")],
            CHOOSING_TYPE: [CallbackQueryHandler(received_type, pattern="^type:")],
            CHOOSING_DATE: [
                CallbackQueryHandler(received_date_choice, pattern="^date:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, received_custom_date),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    subtask_conv = ConversationHandler(
        entry_points=[CommandHandler("addsubtask", add_subtask)],
        states={
            CHOOSING_SUBTASK_TASK: [CallbackQueryHandler(received_subtask_task, pattern="^subtask_task:")],
            TYPING_SUBTASK_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_subtask_title)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_tasks))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("done", done))
    app.add_handler(CommandHandler("taskdetail", task_detail))
    app.add_handler(add_conv)
    app.add_handler(subtask_conv)

    # Callback handlers
    app.add_handler(CallbackQueryHandler(handle_done_callback, pattern="^done:"))
    app.add_handler(CallbackQueryHandler(handle_force_done_callback, pattern="^forcedone:"))
    app.add_handler(CallbackQueryHandler(handle_detail_callback, pattern="^detail:"))
    app.add_handler(CallbackQueryHandler(handle_donesub_callback, pattern="^donesub:"))
    app.add_handler(CallbackQueryHandler(handle_cancel_callback, pattern="^cancel_action$"))

    print("Telegram bot is running...")
    app.run_polling()


def main():
    alexa_thread = threading.Thread(target=run_alexa_server, daemon=True)
    alexa_thread.start()
    print("Alexa server running on port 8001...")
    run_telegram_bot()


if __name__ == "__main__":
    main()