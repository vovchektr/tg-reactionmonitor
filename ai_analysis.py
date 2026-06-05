import html
import json
import logging
import os
import re

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MAX_NEWS_FOR_AI = 15
MAX_TEXT_LEN = 9000


def _clean_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", text).strip()


def _prepare_news(news_items: list[dict]) -> str:
    prepared = []
    for index, item in enumerate(news_items[:MAX_NEWS_FOR_AI], 1):
        title = _clean_text(item.get("title", ""))
        summary = _clean_text(item.get("summary", ""))
        source = _clean_text(item.get("source", ""))
        date = item.get("date")
        date_str = date.strftime("%d.%m.%Y %H:%M") if date else "дата не указана"

        prepared.append(
            f"{index}. Источник: {source}\n"
            f"Дата: {date_str}\n"
            f"Заголовок: {title}\n"
            f"Описание: {summary}"
        )

    return "\n\n".join(prepared)[:MAX_TEXT_LEN]


def _empty_analysis(message: str) -> dict:
    return {
        "summary": message,
        "key_topics": [],
        "narratives": [],
        "conclusion": "AI-анализ не был выполнен.",
    }


def _parse_ai_response(content: str) -> dict:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        logger.warning("OpenAI returned non-JSON response: %s", content)
        return {
            "summary": content.strip(),
            "key_topics": [],
            "narratives": [],
            "conclusion": "Модель вернула текстовый ответ без JSON-структуры.",
        }

    return {
        "summary": str(data.get("summary", "")).strip(),
        "key_topics": data.get("key_topics", []) if isinstance(data.get("key_topics"), list) else [],
        "narratives": data.get("narratives", []) if isinstance(data.get("narratives"), list) else [],
        "conclusion": str(data.get("conclusion", "")).strip(),
    }


async def analyze_news_with_ai(news_items: list[dict]) -> dict:
    if not news_items:
        return _empty_analysis("Нет новостей для AI-анализа.")

    if not OPENAI_API_KEY:
        return _empty_analysis(
            "OPENAI_API_KEY не задан. Добавьте ключ OpenAI в .env, чтобы включить AI-анализ."
        )

    news_text = _prepare_news(news_items)
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)

    prompt = (
        "Ты аналитик медиа и информационной повестки. "
        "Проанализируй список новостей на русском языке. "
        "Верни только JSON без markdown в таком формате:\n"
        "{\n"
        '  "summary": "краткая сводка в 2-4 предложениях",\n'
        '  "key_topics": ["тема 1", "тема 2", "тема 3"],\n'
        '  "narratives": ["нарратив 1", "нарратив 2"],\n'
        '  "conclusion": "аналитический вывод в 2-3 предложениях"\n'
        "}\n\n"
        f"Новости:\n{news_text}"
    )

    try:
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "Ты помогаешь превращать новости в краткую аналитическую сводку.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        content = response.choices[0].message.content or ""
        return _parse_ai_response(content)
    except Exception as exc:
        logger.error("OpenAI analysis error: %s", exc, exc_info=True)
        return _empty_analysis("Не удалось выполнить AI-анализ. Проверьте ключ OpenAI и подключение.")


def _format_list(items: list[str]) -> list[str]:
    return [f"• {html.escape(str(item))}" for item in items if str(item).strip()]


def format_ai_analysis(analysis: dict, title: str = "AI-сводка") -> str:
    lines = [
        f"🤖 <b>{html.escape(title)}</b>",
        "",
        f"<b>Краткая сводка:</b>\n{html.escape(analysis.get('summary', ''))}",
        "",
        "<b>Ключевые темы:</b>",
    ]

    topics = _format_list(analysis.get("key_topics", []))
    lines.extend(topics or ["• Не определены"])

    lines.extend(["", "<b>Основные нарративы:</b>"])
    narratives = _format_list(analysis.get("narratives", []))
    lines.extend(narratives or ["• Не определены"])

    lines.extend([
        "",
        f"<b>Аналитический вывод:</b>\n{html.escape(analysis.get('conclusion', ''))}",
    ])

    return "\n".join(lines).strip()
