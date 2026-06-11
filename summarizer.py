"""
Free news categorization — no external API needed.
Uses keyword matching for category detection.
Output is HTML-safe for Telegram.
"""

import html
import re
from dataclasses import dataclass

CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("💻 Технологии", [
        "технолог", "apple", "google", "microsoft", "android", "iphone", "samsung",
        "программ", "разработ", "стартап", " it ", "интернет", "crypto", "крипто",
        "блокчейн", "нейросет", "искусственный интеллект", " ии ", " ai ", "openai",
        "chatgpt", "гаджет", "tesla", "илон маск", "elon musk", "робот", "автопилот",
        "смартфон", "ноутбук", "процессор", "чип", "nvidia", "intel", "amd",
        "кибербезопасност", "хакер", "утечка данных", "приложени",
    ]),
    ("🏛 Политика", [
        "политик", "президент", "правительств", "парламент", "выбор", "партия", "закон",
        "санкц", "дипломат", "министр", "кремл", "белый дом", "вашингтон", "нато",
        "оон", "госдума", "сенат", "конгресс", "выборы", "референдум", "оппозиц",
        "путин", "байден", "трамп", "зеленск", "макрон", "шольц",
    ]),
    ("💰 Экономика", [
        "экономик", "ввп", "инфляц", "рубл", "доллар", "евро", "банк", "бирж", "акци",
        "нефт", "газ", "бюджет", "налог", "кредит", "рынок", "торговл", "бизнес",
        "ключевая ставка", "цб рф", "центробанк", "фрс", "дефицит", "профицит",
        "импорт", "экспорт", "пошлин", "инвестиц", "акцион", "мвф", "всемирный банк",
    ]),
    ("🌍 Мир", [
        "украин", "россия", "китай", "европ", "ближний восток", "израил", "иран",
        "конфликт", "международ", "война", "беженц", "африк",
        "латинская америка", "азия", "бомбардировк", "обстрел", "перемири", "переговор",
    ]),
    ("🔬 Наука", [
        "наук", "исследован", "учён", "открыт", "физик", "химик", "биолог", "космос",
        "nasa", "роскосмос", "медицин", "здоровь", "вакцин", "вирус", "ковид",
        "климат", "экологи", "генетик", "днк", "ракет", "спутник",
        "марс", "луна", "астрономи", "квантов",
    ]),
    ("⚽ Спорт", [
        "спорт", "футбол", "хоккей", "чемпионат", "олимпи", "матч", "турнир", "игрок",
        "тренер", "команд", "лига", "кубок", "чемпион", "финал", "полуфинал",
        "теннис", "формула 1", "nba", "nfl", "нхл", "рпл",
    ]),
    ("🎭 Культура", [
        "кино", "фильм", "музык", "книг", "искусств", "театр", "выставк", "концерт",
        "литератур", "режиссёр", "актёр", "певец", "певица", "альбом", "премьер",
        "оскар", "грэмми", "канн", "нобел", "художник",
    ]),
]

DEFAULT_CATEGORY = "📌 Прочее"
MAX_ITEMS_PER_CATEGORY = 7


@dataclass
class CategorySummary:
    category: str
    summary: str  # HTML-safe


def _detect_category(text: str) -> str:
    lower = text.lower()
    scores: dict[str, int] = {}
    for category, keywords in CATEGORY_RULES:
        score = sum(1 for kw in keywords if kw in lower)
        if score > 0:
            scores[category] = score
    return max(scores, key=lambda c: scores[c]) if scores else DEFAULT_CATEGORY


async def summarize_news(items) -> list[CategorySummary]:
    if not items:
        return []

    groups: dict[str, list] = {}
    for item in items:
        forced = getattr(item, "source_category", None)
        if forced:
            matched = next((c for c, _ in CATEGORY_RULES if forced.lower() in c.lower()), None)
            cat = matched or forced
        else:
            title = getattr(item, "title", "") or getattr(item, "text", "")[:200]
            body = getattr(item, "summary", "") or getattr(item, "text", "")[:400]
            cat = _detect_category(f"{title} {body}")
        groups.setdefault(cat, []).append(item)

    result: list[CategorySummary] = []
    for category, cat_items in sorted(groups.items()):
        lines = []
        seen: set[str] = set()

        for item in cat_items[:MAX_ITEMS_PER_CATEGORY]:
            title = getattr(item, "title", "") or getattr(item, "text", "")[:150]
            title = title.strip()
            key = re.sub(r"\W+", "", title.lower())[:40]
            if key in seen:
                continue
            seen.add(key)

            source = getattr(item, "source_name", "")
            url = getattr(item, "url", "")

            safe_title = html.escape(title)
            safe_source = html.escape(source)

            if url:
                safe_url = html.escape(url)
                lines.append(f'• <a href="{safe_url}">{safe_title}</a> <i>({safe_source})</i>')
            else:
                lines.append(f"• {safe_title} <i>({safe_source})</i>")

        if lines:
            result.append(CategorySummary(category=category, summary="\n".join(lines)))

    return result
