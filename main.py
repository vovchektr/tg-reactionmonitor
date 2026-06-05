import json
import logging
import os
import html
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler,
    ContextTypes, MessageHandler, filters,
)

from news_search import search_news, format_results
from sentiment import analyze_sentiment, format_sentiment_report
from ai_analysis import analyze_news_with_ai, format_ai_analysis

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")


def _monitor_keyboard(offset: int, total: int, limit: int = 5) -> InlineKeyboardMarkup | None:
    next5 = offset + limit
    next10 = offset + limit * 2
    buttons = []
    if next5 < total:
        buttons.append(InlineKeyboardButton(
            f"Ещё 5 статей ({next5 + 1}–{min(next5 + 5, total)})",
            callback_data=json.dumps({"a": "mon", "o": next5, "l": 5}),
        ))
    if next10 < total:
        buttons.append(InlineKeyboardButton(
            f"Ещё 10 статей ({offset + limit + 1}–{min(offset + limit + 10, total)})",
            callback_data=json.dumps({"a": "mon", "o": next5, "l": 10}),
        ))
    if not buttons:
        return None
    return InlineKeyboardMarkup([buttons])


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
        "/monitor &lt;запрос&gt; — поиск + анализ тональности + AI-сводка\n"
        "/report &lt;запрос&gt; — аналитическая записка по новостям\n\n"
        "Примеры:\n"
        "/news санкции нефть\n"
        "/monitor инфляция экономика\n"
        "/report инфляция экономика"
    )
    await update.message.reply_text(help_text, parse_mode="HTML")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "✅ Бот работает нормально.\n"
        "📡 Подключено источников: 11"
    )


async def news_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = " ".join(context.args).strip() if context.args else ""
    if not query:
        await update.message.reply_text("Укажите поисковый запрос.\nПример: /news санкции нефть")
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
            "Укажите запрос для мониторинга.\nПример: /monitor инфляция экономика"
        )
        return
    if len(query) < 2:
        await update.message.reply_text("Запрос слишком короткий. Введите хотя бы 2 символа.")
        return

    msg = await update.message.reply_text("📡 Собираю данные, анализирую тональность и готовлю AI-сводку...")
    try:
        data = await search_news(query)
        all_texts = [f"{item['title']} {item['summary']}" for item in data["results"]]
        sentiment = analyze_sentiment(all_texts)
        ai_analysis = await analyze_news_with_ai(data["results"])

        text = format_sentiment_report(query, data, sentiment, offset=0, limit=5)
        text = f"{text}\n\n{format_ai_analysis(ai_analysis)}"
        keyboard = _monitor_keyboard(offset=0, total=data["total"])

        context.user_data["monitor"] = {
            "data": data,
            "sentiment": sentiment,
            "query": query,
            "ai_analysis": ai_analysis,
        }

        await msg.edit_text(text, parse_mode="HTML", disable_web_page_preview=True,
                            reply_markup=keyboard)
    except Exception as exc:
        logger.error("Ошибка мониторинга: %s", exc, exc_info=True)
        await msg.edit_text("⚠️ Произошла ошибка при анализе. Попробуйте позже.")


async def monitor_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query_obj = update.callback_query
    await query_obj.answer()

    try:
        payload = json.loads(query_obj.data)
        if payload.get("a") != "mon":
            return
        offset = int(payload["o"])
        limit = int(payload["l"])
    except Exception:
        return

    saved = context.user_data.get("monitor")
    if not saved:
        await query_obj.edit_message_text("⚠️ Данные устарели. Выполните /monitor заново.")
        return

    data = saved["data"]
    sentiment = saved["sentiment"]
    query = saved["query"]
    ai_analysis = saved.get("ai_analysis")

    text = format_sentiment_report(query, data, sentiment, offset=offset, limit=limit)
    if ai_analysis:
        text = f"{text}\n\n{format_ai_analysis(ai_analysis)}"
    keyboard = _monitor_keyboard(offset=offset, total=data["total"], limit=limit)

    await query_obj.edit_message_text(
        text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=keyboard
    )


async def report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = " ".join(context.args).strip() if context.args else ""
    if not query:
        await update.message.reply_text(
            "Укажите запрос для аналитической записки.\nПример: /report инфляция экономика"
        )
        return
    if len(query) < 2:
        await update.message.reply_text("Запрос слишком короткий. Введите хотя бы 2 символа.")
        return

    msg = await update.message.reply_text("📝 Собираю новости и готовлю аналитическую записку...")
    try:
        data = await search_news(query)
        all_texts = [f"{item['title']} {item['summary']}" for item in data["results"]]
        sentiment = analyze_sentiment(all_texts)
        ai_analysis = await analyze_news_with_ai(data["results"])

        text = "\n\n".join([
            f"📝 <b>Аналитическая записка: «{html.escape(query)}»</b>",
            f"Найдено материалов: {data['total']}",
            (
                "Тональность: "
                f"{sentiment.color_label}, индекс {sentiment.score:+.2f} "
                f"(позитив {sentiment.pos_pct:.1f}%, негатив {sentiment.neg_pct:.1f}%, "
                f"нейтрально {sentiment.neu_pct:.1f}%)"
            ),
            format_ai_analysis(ai_analysis, title="AI-аналитика"),
        ])

        await msg.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)
    except Exception as exc:
        logger.error("Ошибка генерации отчета: %s", exc, exc_info=True)
        await msg.edit_text("⚠️ Произошла ошибка при подготовке отчета. Попробуйте позже.")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Получено сообщение: %s", update.message.text)


def main() -> None:
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не задан.")
        raise ValueError("BOT_TOKEN is required.")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("news", news_search))
    app.add_handler(CommandHandler("monitor", monitor))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(CallbackQueryHandler(monitor_page, pattern=r'^\{"a": "mon"'))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    logger.info("Бот запускается...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
