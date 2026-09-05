"""Russian Telegram presentation for the MMA channel."""

from datetime import datetime
from html import escape

from generation.text import fit_text_to_html_limit


MESSAGE_LIMIT = 4000
PHOTO_CAPTION_LIMIT = 1000

CATEGORY_LABELS = {
    "fight_cancelled": "🚨 БОЙ ОТМЕНЁН",
    "injury": "🩹 ТРАВМА",
    "fight_result": "🏆 РЕЗУЛЬТАТ",
    "fight_announcement": "🔥 НОВЫЙ БОЙ",
    "retirement": "🥊 ЗАВЕРШЕНИЕ КАРЬЕРЫ",
    "contract_move": "📝 КОНТРАКТ",
    "event_update": "📅 ТУРНИР",
    "statement": "🎙 ЗАЯВЛЕНИЕ",
    "fighter_news": "🥋 MMA",
}

CATEGORY_TAGS = {
    "fight_cancelled": "#MMA",
    "injury": "#MMA",
    "fight_result": "#MMAResults",
    "fight_announcement": "#MMAFight",
    "retirement": "#MMA",
    "contract_move": "#MMA",
    "event_update": "#MMAEvent",
    "statement": "#MMA",
    "fighter_news": "#MMA",
}


def format_post(news_item):
    """Build one HTML-safe Telegram text message."""

    return _format(news_item, MESSAGE_LIMIT)


def format_photo_caption(news_item):
    """Build one HTML-safe Telegram photo caption."""

    return _format(news_item, PHOTO_CAPTION_LIMIT)


def _format(news_item, limit):
    title = escape(str(news_item.get("title") or "Без заголовка")[:500])
    source = escape(str(news_item.get("source") or "Источник не указан"))
    url = escape(str(news_item.get("url") or ""), quote=True)
    category = news_item.get("event_category")
    label = CATEGORY_LABELS.get(category, CATEGORY_LABELS["fighter_news"])
    tags = _hashtags(news_item)

    header_blocks = []
    if news_item.get("is_rumor"):
        header_blocks.append(
            "👀 <b>СЛУХ</b>\nПока официально не подтверждено."
        )
    header_blocks.append(f"{label}\n<b>{title}</b>")

    footer = (
        f"📅 {_format_date(news_item.get('published_at'))}\n"
        f"📰 {source}\n\n"
        f'🔗 <a href="{url}">Источник</a>'
    )
    if tags:
        footer = f"{footer}\n\n{tags}"

    fixed = "\n\n".join((*header_blocks, footer))
    body = news_item.get("article_text") or news_item.get("description", "")
    body = fit_text_to_html_limit(body, max(0, limit - len(fixed) - 2))

    blocks = [*header_blocks]
    if body:
        blocks.append(escape(body))
    blocks.append(footer)
    return "\n\n".join(blocks)


def _hashtags(news_item):
    tags = [CATEGORY_TAGS.get(news_item.get("event_category"), "#MMA")]
    tags.extend(
        f"#{promotion.upper()}"
        for promotion in news_item.get("matched_promotions", [])[:2]
    )
    if news_item.get("is_rumor"):
        tags.append("#Слух")
    return " ".join(dict.fromkeys(tags))


def _format_date(value):
    if not isinstance(value, datetime):
        return "Дата не указана"
    return value.strftime("%d.%m.%Y")
