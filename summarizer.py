"""
Free news categorization and summarization — no external API needed.
Uses keyword matching for category detection and extractive summarization.
"""

import re
from dataclasses import dataclass

# Keywords for category detection (Russian + English, lowercase substrings)
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
        "путин", "байден", "трамп", "зеленск", "байден", "макрон", "шольц",
    ]),
    ("💰 Экономика", [
        "экономик", "ввп", "инфляц", "рубл", "доллар", "евро", "банк", "бирж", "акци",
        "нефт", "газ", "бюджет", "налог", "кредит", "рынок", "торговл", "бизнес",
        "ключевая ставка", "цб рф", "центробанк", "фрс", "дефицит", "профицит",
        "ввп", "ввс", "импорт", "экспорт", "пошлин", "инвестиц", "акцион",
        "мвф", "всемирный банк", "биткоин", "нефтяно",
    ]),
    ("🌍 Мир", [
        "украин", "россия", "китай", "европ", "ближний восток", "израил", "иран",
        "конфликт", "международ", "война", "мир", "беженц", "нато", "сша", "africa",
        "латинская америка", "азия", "ближний восток", "бомбардировк", "обстрел",
        "перемири", "переговор",
    ]),
    ("🔬 Наука", [
        "наук", "исследован", "учён", "открыт", "физик", "химик", "биолог", "космос",
        "nasa", "роскосмос", "медицин", "здоровь", "вакцин", "вирус", "ковид",
        "пандеми", "климат", "экологи", "генетик", "днк", "ракет", "спутник",
        "марс", "луна", "астрономи", "квантов",
    ]),
    ("⚽ Спорт", [
        "спорт", "футбол", "хоккей", "чемпионат", "олимпи", "матч", "турнир", "игрок",
        "тренер", "команд", "лига", "кубок", "чемпион", "финал", "полуфинал",
        "теннис", "формула 1", "мба", "nba", "nfl", "нхл", "рпл", "еврокубк",
    ]),
    ("🎭 Культура", [
        "кино", "фильм", "музык", "книг", "искусств", "театр", "выставк", "концерт",
        "литератур", "режиссёр", "актёр", "певец", "певица", "альбом", "премьер",
        "оскар", "грэмми", "канн", "нобел", "художник", "скульптур",
    ]),
]

DEFAULT_CATEGORY = "📌 Прочее"
MAX_ITEMS_PER_CATEGORY = 7


@dataclass
class CategorySummary:
    category: str
    summary: str


def _detect_category(text: str) -> str:
    lower = text.lower()
    scores: dict[str, int] = {}
    for category, keywords in CATEGORY_RULES:
        score = sum(1 for kw in keywords if kw in lower)
        if score > 0:
            scores[category] = score
    if not scores:
        return DEFAULT_CATEGORY
    return max(scores, key=lambda c: scores[c])


def _extract_first_sentence(text: str, max_chars: int = 180) -> str:
    """Return first meaningful sentence from text."""
    text = re.sub(r"\s+", " ", text).strip()
    # Try to split on sentence endings
    for sep in (". ", ".\n", "! ", "? "):
        idx = text.find(sep)
        if 30 < idx < max_chars:
            return text[: idx + 1].strip()
    return text[:max_chars].strip() + ("…" if len(text) > max_chars else "")


async def summarize_news(items) -> list[CategorySummary]:
    if not items:
        return []

    groups: dict[str, list] = {}
    for item in items:
        # Use source_category override if set, otherwise auto-detect
        forced = getattr(item, "source_category", None)
        if forced:
            # Map forced category to an icon version if possible
            matched = next(
                (c for c, _ in CATEGORY_RULES if forced.lower() in c.lower()), None
            )
            cat = matched or forced
        else:
            title = getattr(item, "title", "") or getattr(item, "text", "")[:200]
            body = getattr(item, "summary", "") or getattr(item, "text", "")[:400]
            cat = _detect_category(f"{title} {body}")

        groups.setdefault(cat, []).append(item)

    result: list[CategorySummary] = []
    for category, cat_items in sorted(groups.items()):
        lines = []
        seen_titles: set[str] = set()

        for item in cat_items[:MAX_ITEMS_PER_CATEGORY]:
            title = getattr(item, "title", "") or getattr(item, "text", "")[:150]
            title = title.strip()

            # Deduplicate similar headlines
            key = re.sub(r"\W+", "", title.lower())[:40]
            if key in seen_titles:
                continue
            seen_titles.add(key)

            source = getattr(item, "source_name", "")
            url = getattr(item, "url", "")

            if url:
                lines.append(f"• [{title}]({url}) _({source})_")
            else:
                lines.append(f"• {title} _({source})_")

        if lines:
            result.append(CategorySummary(
                category=category,
                summary="\n".join(lines),
            ))

    return result
