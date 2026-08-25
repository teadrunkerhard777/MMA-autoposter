"""Telegram presentation owned entirely by the ExampleNews project."""

from datetime import datetime
from html import escape

from generation.text import fit_text_to_html_limit


MESSAGE_LIMIT = 4000
PHOTO_CAPTION_LIMIT = 1000


def format_post(news_item):
    """Build one HTML-safe text message."""

    return _format(news_item, MESSAGE_LIMIT)


def format_photo_caption(news_item):
    """Build one shorter HTML-safe photo caption."""

    return _format(news_item, PHOTO_CAPTION_LIMIT)


def _format(news_item, limit):
    title = escape(news_item.get("title", "Untitled")[:500])
    source = escape(news_item.get("source", "Unknown source"))
    url = escape(news_item.get("url", ""), quote=True)
    date = _format_date(news_item.get("published_at"))
    tags = " ".join(
        f"#{topic.replace(' ', '')}"
        for topic in news_item.get("matched_topics", [])[:4]
    )
    footer = (
        f"📅 {date}\n"
        f"📰 {source}\n\n"
        f'🔗 <a href="{url}">Read source</a>'
    )

    if tags:
        footer = f"{footer}\n\n{tags}"

    header = f"🟦 <b>{title}</b>"
    fixed_length = len(header) + len(footer) + 4
    body = (
        news_item.get("article_text")
        or news_item.get("description", "")
    )
    body = fit_text_to_html_limit(body, max(0, limit - fixed_length))

    if body:
        return f"{header}\n\n{escape(body)}\n\n{footer}"

    return f"{header}\n\n{footer}"


def _format_date(value):
    if not isinstance(value, datetime):
        return "Date unknown"

    return value.strftime("%Y-%m-%d")

