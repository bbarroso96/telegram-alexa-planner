from dotenv import load_dotenv
load_dotenv()

from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, filters,
)
from config.settings import config
from bot.handlers import (
    start, add_task, list_tasks, today, done, done_subtask,
    add_subtask, task_detail, cancel,
    received_title, received_category, received_type,
    received_date_choice, received_custom_date,
    TYPING_TITLE, CHOOSING_CATEGORY, CHOOSING_TYPE, CHOOSING_DATE,
)


def main():
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

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_tasks))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("done", done))
    app.add_handler(CommandHandler("donesub", done_subtask))
    app.add_handler(CommandHandler("subtask", add_subtask))
    app.add_handler(CommandHandler("task", task_detail))
    app.add_handler(add_conv)

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()