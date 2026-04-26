import logging
import os

from dotenv import load_dotenv
from telegram import BotCommand
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler

from bot.database import Database
from bot.handlers import (
    button_callback,
    checkin_handler,
    create_handler,
    delete_handler,
    history_handler,
    join_handler,
    leave_handler,
    next_handler,
    participants_handler,
    trackers_handler,
)

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


BOT_COMMANDS = [
    BotCommand("create", "Create a new tracker"),
    BotCommand("join", "Join a tracker"),
    BotCommand("leave", "Leave a tracker"),
    BotCommand("checkin", "Check in for a tracker"),
    BotCommand("next", "Who should check in next?"),
    BotCommand("history", "Check-in history (last 2 months)"),
    BotCommand("trackers", "List trackers in this chat"),
    BotCommand("participants", "List participants in a tracker"),
    BotCommand("delete", "Delete a tracker"),
]


async def post_init(application):
    db = Database(os.getenv("DATABASE_PATH", "checkin_bot.db"))
    await db.connect()
    application.bot_data["db"] = db
    await application.bot.set_my_commands(BOT_COMMANDS)
    logger.info("Database connected, commands registered")


async def post_shutdown(application):
    db = application.bot_data.get("db")
    if db:
        await db.close()
        logger.info("Database closed")


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set. Copy .env.example to .env and fill it in.")

    app = (
        ApplicationBuilder()
        .token(token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    app.add_handler(CommandHandler("create", create_handler))
    app.add_handler(CommandHandler("join", join_handler))
    app.add_handler(CommandHandler("leave", leave_handler))
    app.add_handler(CommandHandler("checkin", checkin_handler))
    app.add_handler(CommandHandler("next", next_handler))
    app.add_handler(CommandHandler("history", history_handler))
    app.add_handler(CommandHandler("trackers", trackers_handler))
    app.add_handler(CommandHandler("participants", participants_handler))
    app.add_handler(CommandHandler("delete", delete_handler))
    app.add_handler(CallbackQueryHandler(button_callback))

    logger.info("Bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
