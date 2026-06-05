import re
from dataclasses import dataclass

POSITIVE_WORDS = {
    # Военные и дипломатические успехи России / СВО
    "освободили", "освобождение", "взяли", "наступление", "продвижение", "прорыв",
    "уничтожили", "уничтожена", "поражена", "сбили", "перехватили", "нейтрализовали",
    "капитуляция", "сдались", "победа", "победили", "разгром", "успешно", "успешная",
    "героически", "героический", "подвиг", "орден", "медаль", "награждён", "мужество",
    "оборона", "защита", "отразили", "отбили", "укрепление", "укрепили", "закрепились",
    # Дипломатия и влияние России
    "переговоры", "договор", "соглашение", "подписали", "ратифицировали", "союзник",
    "союзники", "интеграция", "одкб", "снг", "евразийский", "сотрудничество",
    "партнёрство", "партнерство", "поддержка", "поддержали", "признали", "легитимность",
    "суверенитет", "независимость", "самостоятельность", "влияние", "авторитет",
    "лидерство", "инициатива", "предложение принято", "согласились",
    # Экономика и санкционная устойчивость
    "рост", "растёт", "растет", "вырос", "выросла", "выросли", "рекорд",
    "увеличение", "прибыль", "доходы", "профицит", "импортозамещение",
    "технологический суверенитет", "локализация", "инвестиции", "развитие", "прогресс",
    "стабильность", "стабилизация", "восстановление", "диверсификация", "экспорт",
    "санкции не работают", "обход санкций", "адаптация", "льготы", "субсидии",
    # Положительные для Пашиняна / Армении в контексте ОДКБ
    "вернулся", "возобновил", "одкб", "интеграция армении",
}

NEGATIVE_WORDS = {
    # Критика России / армии / правительства
    "критикует россию", "критика кремля", "осудила россию", "осудили россию",
    "обвинила россию", "обвиняет россию", "давление на россию", "изоляция",
    "агрессия", "оккупация", "аннексия", "незаконный", "преступление",
    "военное преступление", "геноцид", "репрессии", "диктатура", "авторитаризм",
    # Санкции против России
    "санкции", "санкция", "ограничения", "запрет", "заморозка активов",
    "отключение swift", "эмбарго", "конфискация", "арест активов",
    # Провалы и потери в СВО
    "отступление", "отошли", "отступили", "провал", "поражение", "провальный",
    "потери", "потеря", "погибли", "погиб", "погибла", "жертвы", "уничтожены",
    "сбит", "сбита", "подбит", "подбита", "захвачен", "захвачена", "плен",
    # Нарратив про-Украина / НАТО
    "нато расширяется", "вступление в нато", "поставки оружия украине",
    "военная помощь украине", "украина победила", "украина наступает",
    "прорыв украины", "успех украины", "контрнаступление украины",
    "западная поддержка украины", "солидарность с украиной",
    # Ослабление влияния России / выход из ОДКБ
    "выход из одкб", "покидает одкб", "против одкб", "критика одкб",
    "пашинян против", "пашинян отказался", "пашинян заблокировал",
    "армения покидает", "армения выходит", "разрыв отношений",
    "антироссийский", "антироссийская", "русофобия", "русофобский",
    # Экономические проблемы России
    "обвал", "обвалился", "рецессия", "дефолт", "банкротство", "кризис",
    "инфляция", "безработица", "дефицит бюджета", "падение рубля",
    "утечка мозгов", "отток капитала", "релокация бизнеса",
    # Внутреннее давление
    "протест", "протесты", "беспорядки", "задержан", "арестован", "осуждён",
    "репрессии", "цензура", "преследование", "эмиграция", "бегство",
}

NEUTRAL_BOOSTERS = {
    "заявил", "сообщил", "сообщила", "отметил", "отметила", "рассказал", "рассказала",
    "прокомментировал", "пояснил", "пояснила", "уточнил", "уточнила", "сказал", "сказала",
    "считает", "полагает", "предполагает", "обсудили", "рассмотрели", "состоялся",
    "прошёл", "прошла", "прошло", "встреча", "переговоры", "совещание", "брифинг",
    "планируется", "ожидается", "намечается", "по данным", "по информации", "источники",
}


def _clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).lower().strip()


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[а-яёА-ЯЁa-zA-Z]+", _clean(text))


def _count_hits(text: str, word_set: set) -> int:
    cleaned = _clean(text)
    tokens = set(_tokenize(text))
    hits = 0
    for phrase in word_set:
        if " " in phrase:
            if phrase in cleaned:
                hits += 1
        else:
            if phrase in tokens:
                hits += 1
    return hits


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
        p_hits = _count_hits(text, POSITIVE_WORDS)
        n_hits = _count_hits(text, NEGATIVE_WORDS)

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
