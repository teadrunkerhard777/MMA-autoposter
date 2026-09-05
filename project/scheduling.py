"""Project-owned time semantics for news and scheduled MMA content."""

from datetime import datetime, timedelta, timezone

from processing.filters import filter_by_date


EVERGREEN_QUEUE = "evergreen"


def filter_time_eligible(news_items, lookback_days, now=None):
    """Keep fresh news and evergreen items whose schedule time has arrived."""

    current_time = _utc_now(now)
    news = []
    evergreen = []

    for item in news_items:
        if item.get("content_queue") == EVERGREEN_QUEUE:
            scheduled_at = reliable_datetime(item.get("scheduled_at"))
            if scheduled_at is not None and scheduled_at <= current_time:
                evergreen.append(item)
            continue
        news.append(item)

    return filter_by_date(news, lookback_days, current_time) + evergreen


def event_window(event_at, now=None):
    """Classify a reliable event date without inventing missing time data."""

    event_time = reliable_datetime(event_at)
    if event_time is None:
        return None

    delta = event_time - _utc_now(now)
    if delta < timedelta(0):
        return "past"
    if delta <= timedelta(hours=48):
        return "next_48_hours"
    if delta <= timedelta(days=7):
        return "next_7_days"
    return "later"


def reliable_datetime(value):
    """Return a timezone-aware UTC datetime or None for unreliable values."""

    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    if not isinstance(value, datetime) or value.tzinfo is None:
        return None
    return value.astimezone(timezone.utc)


def _utc_now(now=None):
    value = now or datetime.now(timezone.utc)
    normalized = reliable_datetime(value)
    if normalized is None:
        raise ValueError("now must be timezone-aware")
    return normalized
