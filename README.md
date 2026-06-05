# 📰 TG Media Monitor Bot

**Telegram bot for monitoring news and sentiment analysis in Russian-language media.**

Helps media analysts, journalists, and anyone interested to quickly understand public reaction to current events.

## Features

- `/monitor <query>` — search news + **full sentiment analysis** (positive/negative/neutral with percentages and colors)
- `/news <query>` — quick news search
- `/sources` — list of monitored sources
- `/help` — show help

## Examples

```bash
/monitor Крым
/monitor Пашинян
/monitor СВО
/monitor бензин
/news перемирие

## Sources (12+)

Lenta.ru, RBC, Kommersant, TASS, Meduza, Izvestia, Rossiyskaya Gazeta, Fontanka and others.

## Technologies

- Python
- RSS parsing
- Custom sentiment analyzer with geopolitical context rules (Russia-focused)

## Development Plans

- Comment analysis under posts (v2.0)
- Ability to add custom Telegram channels
- Automatic notifications (`/track`)
- Daily digests