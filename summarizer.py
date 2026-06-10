"""Uses Claude API to categorize and summarize news."""

import logging
from dataclasses import dataclass

import anthropic

from config import ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)

CATEGORIES = [
    "Технологии",
    "Политика",
    "Экономика",
    "Мир",
    "Наука",
    "Спорт",
    "Культура",
    "Прочее",
]

SYSTEM_PROMPT = """Ты помощник, который составляет краткие новостные сводки на русском языке.
Тебе дают список новостей. Нужно:
1. Сгруппировать по тематическим категориям
2. Для каждой категории написать краткое резюме (2-4 предложения) о главных событиях
Отвечай строго в формате:
## НазваниеКатегории
Краткое описание...

Не добавляй ничего лишнего до или после блоков."""


@dataclass
class CategorySummary:
    category: str
    summary: str


def _build_news_text(items) -> str:
    lines = []
    for i, item in enumerate(items[:100], 1):  # cap at 100 items
        source = getattr(item, "source_name", "?")
        title = getattr(item, "title", "") or getattr(item, "text", "")[:120]
        cat = getattr(item, "source_category", None)
        category_hint = f" [{cat}]" if cat else ""
        lines.append(f"{i}. [{source}{category_hint}] {title}")
    return "\n".join(lines)


async def summarize_news(items) -> list[CategorySummary]:
    if not items:
        return []

    if not ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY not set — returning raw sources without summary")
        return _fallback_summary(items)

    news_text = _build_news_text(items)
    user_message = (
        f"Вот новости за последние 24 часа:\n\n{news_text}\n\n"
        "Составь сводку по категориям."
    )

    try:
        client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        raw = response.content[0].text
        return _parse_response(raw)

    except Exception as e:
        logger.warning(f"Summarizer error: {e}")
        return _fallback_summary(items)


def _parse_response(text: str) -> list[CategorySummary]:
    summaries: list[CategorySummary] = []
    current_cat: str | None = None
    current_lines: list[str] = []

    for line in text.splitlines():
        if line.startswith("## "):
            if current_cat and current_lines:
                summaries.append(CategorySummary(
                    category=current_cat,
                    summary=" ".join(current_lines).strip(),
                ))
            current_cat = line[3:].strip()
            current_lines = []
        elif current_cat and line.strip():
            current_lines.append(line.strip())

    if current_cat and current_lines:
        summaries.append(CategorySummary(
            category=current_cat,
            summary=" ".join(current_lines).strip(),
        ))

    return summaries


def _fallback_summary(items) -> list[CategorySummary]:
    """Group by source_category without AI when API key is missing."""
    groups: dict[str, list[str]] = {}
    for item in items:
        cat = getattr(item, "source_category", None) or "Прочее"
        title = getattr(item, "title", "") or getattr(item, "text", "")[:100]
        groups.setdefault(cat, []).append(title)

    result = []
    for cat, titles in groups.items():
        snippet = " • ".join(titles[:5])
        result.append(CategorySummary(category=cat, summary=snippet))
    return result
