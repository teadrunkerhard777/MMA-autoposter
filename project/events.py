"""Conservative event-date extraction for Russian MMA material."""

import re
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from project.scheduling import reliable_datetime, reliable_event_date


MOSCOW_TIMEZONE = ZoneInfo("Europe/Moscow")
EVENT_DATE_CATEGORIES = {
    "event_update",
    "fight_announcement",
    "fight_cancelled",
    "fight_result",
    "injury",
}
RUSSIAN_MONTHS = {
    "января": 1,
    "февраля": 2,
    "марта": 3,
    "апреля": 4,
    "мая": 5,
    "июня": 6,
    "июля": 7,
    "августа": 8,
    "сентября": 9,
    "октября": 10,
    "ноября": 11,
    "декабря": 12,
}
DATE_PATTERN = re.compile(
    rf"(?<!\d)([0-3]?\d)\s+({'|'.join(RUSSIAN_MONTHS)})"
    r"(?:\s+(\d{4})(?:\s+года)?)?",
    flags=re.IGNORECASE,
)
MOSCOW_TIME_PATTERN = re.compile(
    r"(?:в|—|-)\s*([01]?\d|2[0-3]):([0-5]\d)\s*"
    r"(?:по\s+московскому\s+времени|(?:по\s+)?мск)",
    flags=re.IGNORECASE,
)


def enrich_event_timing(news_item):
    """Attach only an explicitly stated event date and Moscow time."""

    if news_item.get("event_category") not in EVENT_DATE_CATEGORIES:
        return news_item
    if reliable_datetime(news_item.get("event_at")) is not None:
        return news_item
    if reliable_event_date(news_item.get("event_date")) is not None:
        return news_item

    published_at = reliable_datetime(news_item.get("published_at"))
    if published_at is None:
        return news_item

    text = " ".join(
        str(news_item.get(key) or "")
        for key in ("title", "description", "article_text")
    )
    event_date = _select_event_date(
        text,
        published_at.astimezone(MOSCOW_TIMEZONE).date(),
        news_item.get("event_category"),
    )
    if event_date is None:
        return news_item

    news_item["event_date"] = event_date.isoformat()
    news_item["event_date_source"] = "article_explicit"
    times = {
        (int(match.group(1)), int(match.group(2)))
        for match in MOSCOW_TIME_PATTERN.finditer(text)
    }

    if len(times) == 1:
        hour, minute = next(iter(times))
        news_item["event_at"] = datetime.combine(
            event_date,
            time(hour, minute),
            tzinfo=MOSCOW_TIMEZONE,
        )
        news_item["event_date_precision"] = "minute"
    else:
        news_item["event_date_precision"] = "date"

    return news_item


def _select_event_date(text, published_date, category):
    candidates = []

    for match in DATE_PATTERN.finditer(text):
        day = int(match.group(1))
        month = RUSSIAN_MONTHS[match.group(2).casefold()]
        explicit_year = match.group(3)
        year = int(explicit_year) if explicit_year else published_date.year

        try:
            candidate = date(year, month, day)
        except ValueError:
            continue

        if not explicit_year and candidate < published_date - timedelta(days=60):
            try:
                candidate = date(year + 1, month, day)
            except ValueError:
                continue

        candidates.append(candidate)

    if category == "fight_result":
        candidates = [
            candidate
            for candidate in candidates
            if published_date - timedelta(days=7)
            <= candidate
            <= published_date + timedelta(days=1)
        ]
        return min(
            candidates,
            key=lambda candidate: abs(candidate - published_date),
            default=None,
        )

    candidates = [
        candidate
        for candidate in candidates
        if published_date - timedelta(days=1)
        <= candidate
        <= published_date + timedelta(days=370)
    ]
    return min(candidates, default=None)
