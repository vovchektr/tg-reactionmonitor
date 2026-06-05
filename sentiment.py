import re
from dataclasses import dataclass

POSITIVE_WORDS = {
    "рост", "растёт", "растет", "вырос", "выросла", "выросли", "увеличился", "увеличилась",
    "увеличение", "улучшение", "улучшился", "улучшилась", "прибыль", "прибыли", "доход",
    "доходы", "успех", "успехи", "победа", "победы", "победили", "выиграл", "выиграли",
    "достижение", "достижения", "рекорд", "рекорды", "позитивный", "позитивно",
    "оптимизм", "оптимистичный", "укрепление", "укрепился", "укрепилась", "стабилизация",
    "восстановление", "восстановился", "поддержка", "помощь", "соглашение", "договор",
    "мир", "примирение", "сотрудничество", "партнёрство", "партнерство", "инвестиции",
    "развитие", "прогресс", "открытие", "запуск", "внедрение", "расширение", "лидирует",
    "лидер", "одобрение", "одобрили", "поддержали", "подписали", "ратифицировали",
    "снижение цен", "дешевле", "бесплатно", "льготы", "субсидии", "повышение зарплат",
    "урегулирование", "решение принято", "стабильность", "безопасность", "спасли",
    "выжил", "выжили", "спасение", "освобождение", "освободили", "возобновил",
    "прорыв", "хороший", "хорошая", "отличный", "отличная", "эффективный",
}

NEGATIVE_WORDS = {
    "кризис", "обвал", "обвалился", "обвалилась", "падение", "упал", "упала", "упали",
    "снижение", "сокращение", "убыток", "убытки", "потери", "потеря", "дефицит",
    "санкции", "ограничения", "запрет", "запреты", "конфликт", "война", "боевые",
    "атака", "удар", "обстрел", "взрыв", "теракт", "жертвы", "погибли", "погиб",
    "погибла", "раненые", "ранен", "ранены", "катастрофа", "авария", "крушение",
    "катастрофический", "трагедия", "провал", "поражение", "проиграл", "проиграли",
    "банкротство", "банкрот", "долг", "долги", "дефолт", "инфляция", "безработица",
    "рецессия", "коллапс", "кризисный", "опасность", "угроза", "угрозы", "риск",
    "скандал", "коррупция", "арест", "задержан", "задержали", "осудили", "приговор",
    "штраф", "санкция", "протест", "беспорядки", "митинг", "забастовка",
    "ухудшение", "ухудшился", "ухудшилась", "вырос долг", "дорожает", "дорожание",
    "сбой", "отказ", "проблема", "проблемы", "критика", "критикуют", "обвинения",
    "обвинил", "скрыл", "ложь", "фейк", "дезинформация", "нарушение", "незаконный",
    "смерть", "гибель", "трагический", "тяжёлый", "тяжелый", "серьёзный", "серьезный",
    "опасный", "критический", "катастрофичный", "разрушение", "уничтожение",
}

NEUTRAL_BOOSTERS = {
    "заявил", "сообщил", "сообщила", "отметил", "отметила", "рассказал", "рассказала",
    "прокомментировал", "пояснил", "пояснила", "уточнил", "уточнила", "сказал", "сказала",
    "считает", "полагает", "предполагает", "обсудили", "рассмотрели", "состоялся",
    "прошёл", "прошла", "прошло", "встреча", "переговоры", "совещание", "брифинг",
    "планируется", "ожидается", "намечается", "по данным", "по информации", "источники",
}


def _tokenize(text: str) -> list[str]:
    text = re.sub(r"<[^>]+>", " ", text)
    return re.findall(r"[а-яёА-ЯЁa-zA-Z]+", text.lower())


@dataclass
class SentimentResult:
    positive: int
    negative: int
    neutral: int
    total: int
    pos_pct: float
    neg_pct: float
    neu_pct: float
    score: float
    label: str

    @property
    def color_label(self) -> str:
        if self.label == "positive":
            return "🟢 Позитивный"
        if self.label == "negative":
            return "🔴 Негативный"
        return "⚪️ Нейтральный"


def analyze_sentiment(texts: list[str]) -> SentimentResult:
    pos = neg = neu = 0
    total = len(texts)

    for text in texts:
        tokens = set(_tokenize(text))
        p_hits = len(tokens & POSITIVE_WORDS)
        n_hits = len(tokens & NEGATIVE_WORDS)

        if p_hits == 0 and n_hits == 0:
            neu += 1
        elif p_hits > n_hits:
            pos += 1
        elif n_hits > p_hits:
            neg += 1
        else:
            neu += 1

    if total == 0:
        return SentimentResult(0, 0, 0, 0, 0.0, 0.0, 0.0, 0.0, "neutral")

    pos_pct = round(pos / total * 100, 1)
    neg_pct = round(neg / total * 100, 1)
    neu_pct = round(100 - pos_pct - neg_pct, 1)
    score = round((pos - neg) / total, 3)

    if pos_pct >= 40 and pos_pct > neg_pct:
        label = "positive"
    elif neg_pct >= 40 and neg_pct > pos_pct:
        label = "negative"
    else:
        label = "neutral"

    return SentimentResult(
        positive=pos, negative=neg, neutral=neu, total=total,
        pos_pct=pos_pct, neg_pct=neg_pct, neu_pct=neu_pct,
        score=score, label=label,
    )


def _bar(pct: float, width: int = 10) -> str:
    filled = round(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)


def format_sentiment_report(query: str, data: dict, sentiment: SentimentResult) -> str:
    results = data["results"]
    total_found = data["total"]

    lines = [
        f"📊 <b>Мониторинг: «{query}»</b>",
        f"Проанализировано статей: {sentiment.total} из {total_found} найденных",
        "",
        "─── Тональность ───",
        f"{sentiment.color_label}  (индекс: {sentiment.score:+.2f})",
        "",
        f"🟢 Позитивных:  {sentiment.pos_pct:5.1f}%  {_bar(sentiment.pos_pct)} ({sentiment.positive})",
        f"🔴 Негативных:  {sentiment.neg_pct:5.1f}%  {_bar(sentiment.neg_pct)} ({sentiment.negative})",
        f"⚪️ Нейтральных: {sentiment.neu_pct:5.1f}%  {_bar(sentiment.neu_pct)} ({sentiment.neutral})",
        "",
    ]

    if results:
        lines.append("─── Свежие материалы ───")
        for i, item in enumerate(results[:5], 1):
            title = item["title"] or "Без заголовка"
            link = item["link"]
            source = item["source"]
            date = item["date"]

            item_text = f"{item['title']} {item['summary']}"
            item_sentiment = analyze_sentiment([item_text])

            s_icon = {"positive": "🟢", "negative": "🔴", "neutral": "⚪️"}[item_sentiment.label]
            date_str = f' · {date.strftime("%d.%m %H:%M")}' if date else ""

            lines.append(f'{i}. {s_icon} <a href="{link}">{title}</a>')
            lines.append(f"    📰 {source}{date_str}")
            lines.append("")
    else:
        lines += [
            "📭 Статьи не найдены.",
            "",
            "💡 <b>Попробуйте:</b>",
            "• Более общее слово",
            "• Убрать кавычки",
            "• Синоним или другую форму слова",
        ]

    if data.get("sources_hit"):
        sources_str = ", ".join(data["sources_hit"][:6])
        if len(data["sources_hit"]) > 6:
            sources_str += f" и ещё {len(data['sources_hit']) - 6}"
        lines.append(f"<i>Источники: {sources_str}</i>")

    return "\n".join(lines).strip()
