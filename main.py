import logging
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я бот для мониторинга реакций и анализа тональности новостей в Telegram-каналах.\n\n"
        "Используйте /help для списка команд."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "Доступные команды:\n"
        "/start — начать работу\n"
        "/help — показать это сообщение\n"
        "/status — статус бота\n"
    )
    await update.message.reply_text(help_text)


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Бот работает нормально.")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Получено сообщение: %s", update.message.text)


def main() -> None:
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не задан. Добавьте его в файл .env или переменные окружения.")
        raise ValueError("BOT_TOKEN is required. Set it in .env or environment variables.")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    logger.info("Бот запускается...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
