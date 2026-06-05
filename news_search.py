import asyncio
import logging
import re
import time
from datetime import datetime, timezone
from typing import Optional

import aiohttp
import feedparser

logger = logging.getLogger(__name__)

RSS_SOURCES = [
    {"name": "Lenta.ru",     "url": "https://lenta.ru/rss/news"},
    {"name": "RBK",          "url": "https://rssexport.rbc.ru/rbcnews/news/30/full.rss"},
    {"name": "Известия",     "url": "https://iz.ru/xml/rss/all.xml"},
    {"name": "Фонтанка",     "url": "https://www.fontanka.ru/fontanka.rss"},
    {"name": "РИА Новости",  "url": "https://feeds.feedburner.com/ria/news"},
    {"name": "ТАСС",         "url": "https://tass.ru/rss/v2.xml"},
    {"name": "Коммерсантъ",  "url": "https://www.kommersant.ru/RSS/news.xml"},
    {"name": "Газета.ru",    "url": "https://www.gazeta.ru/export/rss/lenta.xml"},
    {"name": "Медуза",       "url": "https://meduza.io/rss/all"},
    {"name": "Российская газета", "url": "https://rg.ru/xml/index.xml"},
    {"name": "Новая газета", "url": "https://novayagazeta.ru/rss/all.xml"},
    {"name": "Интерфакс",    "url": "https://www.interfax.ru/rss.asp"},
]

FETCH_TIMEOUT = aiohttp.ClientTimeout(total=10)
MAX_RESULTS = 5
MAX_SUMMARY_LEN = 300


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _entry_text(entry) -> str:
    parts = [
        entry.get("title", ""),
        entry.get("summary", ""),
        entry.get("description", ""),
    ]
    tags = [t.get("term", "") for t in entry.get("tags", [])]
    parts.extend(tags)
    return " ".join(parts).lower()


def _parse_date(entry) -> Optional[datetime]:
    for field in ("published_parsed", "updated_parsed"):
        val = entry.get(field)
        if val:
            try:
                return datetime(*val[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def _matches(entry, keywords: list[str], require_all: bool) -> bool:
    text = _entry_text(entry)
    check = all if require_all else any
    return check(kw in text for kw in keywords)


async def _fetch_feed(session: aiohttp.ClientSession, source: dict) -> list[dict]:
    try:
        async with session.get(source["url"], timeout=FETCH_TIMEOUT, ssl=False) as resp:
            if resp.status != 200:
                logger.debug("Feed %s returned HTTP %s", source["name"], resp.status)
                return []
            content = await resp.read()
        feed = feedparser.parse(content)
        results = []
        for entry in feed.entries:
            results.append({
                "source": source["name"],
                "title": _normalize(entry.get("title", "")),
                "link": entry.get("link", ""),
                "summary": _normalize(entry.get("summary") or entry.get("description", "")),
                "date": _parse_date(entry),
                "entry": entry,
            })
        return results
    except asyncio.TimeoutError:
        logger.debug("Timeout fetching %s", source["name"])
        return []
    except Exception as exc:
        logger.debug("Error fetching %s: %s", source["name"], exc)
        return []


async def search_news(query: str) -> dict:
    raw_keywords = [w.strip().lower() for w in query.split() if w.strip()]
    keywords_exact = [f'"{w}"' in query.lower() for w in raw_keywords]

    require_all = True

    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0 (compatible; TGNewsBot/1.0)"}) as session:
        tasks = [_fetch_feed(session, src) for src in RSS_SOURCES]
        all_feeds = await asyncio.gather(*tasks)

    all_items: list[dict] = []
    for items in all_feeds:
        all_items.extend(items)

    matched = [item for item in all_items if _matches(item["entry"], raw_keywords, require_all=True)]

    if not matched and len(raw_keywords) > 1:
        matched = [item for item in all_items if _matches(item["entry"], raw_keywords, require_all=False)]
        require_all = False

    matched.sort(key=lambda x: x["date"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    sources_hit = list({item["source"] for item in matched})
    top = matched[:MAX_RESULTS]

    return {
        "query": query,
        "keywords": raw_keywords,
        "total": len(matched),
        "results": top,
        "require_all": require_all,
        "sources_fetched": len(all_items),
        "sources_hit": sources_hit,
    }


def format_results(data: dict) -> str:
    results = data["results"]
    total = data["total"]
    query = data["query"]
    require_all = data["require_all"]

    if not results:
        lines = [
            f'🔍 По запросу <b>«{query}»</b> ничего не найдено.',
            "",
            "💡 <b>Попробуйте:</b>",
            "• Использовать более общее слово (например, <i>«война»</i> вместо <i>«военная операция»</i>)",
            "• Убрать кавычки, если запрос в кавычках",
            "• Проверить написание — возможно, опечатка",
            "• Попробовать синоним или другую форму слова",
            "• Снизить детализацию: вместо <i>«санкции против нефти»</i> попробуйте <i>«санкции»</i>",
        ]
        return "\n".join(lines)

    hint = ""
    if not require_all and len(data["keywords"]) > 1:
        hint = "\n⚠️ <i>Найдено по части слов запроса</i>"

    lines = [
        f'🔍 <b>«{query}»</b> — найдено {total} материал(ов){hint}',
        "",
    ]

    for i, item in enumerate(results, 1):
        title = item["title"] or "Без заголовка"
        link = item["link"]
        source = item["source"]
        date = item["date"]
        summary = item["summary"]

        date_str = ""
        if date:
            date_str = f' · {date.strftime("%d.%m %H:%M")}'

        summary_short = ""
        if summary:
            clean = re.sub(r"<[^>]+>", "", summary)
            summary_short = clean[:MAX_SUMMARY_LEN].rstrip()
            if len(clean) > MAX_SUMMARY_LEN:
                summary_short += "…"

        lines.append(f"{i}. <a href=\"{link}\">{title}</a>")
        lines.append(f"   📰 {source}{date_str}")
        if summary_short:
            lines.append(f"   {summary_short}")
        lines.append("")

    if total > MAX_RESULTS:
        lines.append(f"<i>...и ещё {total - MAX_RESULTS} результат(ов). Уточните запрос.</i>")

    return "\n".join(lines).strip()
