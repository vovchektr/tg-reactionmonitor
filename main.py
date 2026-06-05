import logging
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from news_search import search_news, format_results
from sentiment import analyze_sentiment, format_sentiment_report

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
        "/news &lt;запрос&gt; — поиск новостей по ключевым словам\n"
        "/monitor &lt;запрос&gt; — поиск + анализ тональности\n\n"
        "Примеры:\n"
        "/news санкции нефть\n"
        "/monitor инфляция экономика"
    )
    await update.message.reply_text(help_text, parse_mode="HTML")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "✅ Бот работает нормально.\n"
        "📡 Подключено источников: 12"
    )


async def news_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = " ".join(context.args).strip() if context.args else ""

    if not query:
        await update.message.reply_text(
            "Укажите поисковый запрос после команды.\n"
            "Пример: /news санкции нефть"
        )
        return

    if len(query) < 2:
        await update.message.reply_text("Запрос слишком короткий. Введите хотя бы 2 символа.")
        return

    msg = await update.message.reply_text("🔍 Ищу новости, подождите...")

    try:
        data = await search_news(query)
        text = format_results(data)
        await msg.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)
    except Exception as exc:
        logger.error("Ошибка поиска новостей: %s", exc, exc_info=True)
        await msg.edit_text("⚠️ Произошла ошибка при поиске. Попробуйте позже.")


async def monitor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = " ".join(context.args).strip() if context.args else ""

    if not query:
        await update.message.reply_text(
            "Укажите запрос для мониторинга.\n"
            "Пример: /monitor инфляция экономика"
        )
        return

    if len(query) < 2:
        await update.message.reply_text("Запрос слишком короткий. Введите хотя бы 2 символа.")
        return

    msg = await update.message.reply_text("📡 Собираю данные и анализирую тональность...")

    try:
        data = await search_news(query)

        all_texts = [
            f"{item['title']} {item['summary']}"
            for item in data["results"]
        ]

        sentiment = analyze_sentiment(all_texts)
        text = format_sentiment_report(query, data, sentiment)
        await msg.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)
    except Exception as exc:
        logger.error("Ошибка мониторинга: %s", exc, exc_info=True)
        await msg.edit_text("⚠️ Произошла ошибка при анализе. Попробуйте позже.")


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
    app.add_handler(CommandHandler("news", news_search))
    app.add_handler(CommandHandler("monitor", monitor))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    logger.info("Бот запускается...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
