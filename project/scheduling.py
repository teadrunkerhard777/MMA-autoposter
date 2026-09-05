"""Project-owned time semantics for news and scheduled MMA content."""

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from processing.filters import filter_by_date


EVERGREEN_QUEUE = "evergreen"
EDITORIAL_TIMEZONE = ZoneInfo("Europe/Moscow")


def filter_time_eligible(news_items, lookback_days, now=None):
    """Keep fresh news and evergreen items whose schedule time has arrived."""

    current_time = _utc_now(now)
    current_date = current_time.astimezone(EDITORIAL_TIMEZONE).date()
    stale_event_date = current_date - timedelta(days=lookback_days)
    news = []
    evergreen = []

    for item in news_items:
        if item.get("content_queue") == EVERGREEN_QUEUE:
            scheduled_at = reliable_datetime(item.get("scheduled_at"))
            if scheduled_at is not None and scheduled_at <= current_time:
                evergreen.append(item)
            continue

        event_at = reliable_datetime(item.get("event_at"))
        event_date = reliable_event_date(item.get("event_date"))
        if (
            event_at is not None
            and event_at < current_time - timedelta(days=lookback_days)
        ):
            continue
        if (
            event_at is None
            and event_date is not None
            and event_date < stale_event_date
        ):
            continue
        news.append(item)

    return filter_by_date(news, lookback_days, current_time) + evergreen


def event_window(event_at, now=None, event_date=None):
    """Classify a reliable event date without inventing missing time data."""

    event_time = reliable_datetime(event_at)
    if event_time is not None:
        delta = event_time - _utc_now(now)
        if delta < timedelta(0):
            return "past"
        if delta <= timedelta(hours=48):
            return "next_48_hours"
        if delta <= timedelta(days=7):
            return "next_7_days"
        return "later"

    event_day = reliable_event_date(event_date)
    if event_day is None:
        return None

    current_day = _utc_now(now).astimezone(EDITORIAL_TIMEZONE).date()
    days_until = (event_day - current_day).days
    if days_until < 0:
        return "past"
    if days_until <= 2:
        return "next_48_hours"
    if days_until <= 7:
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


def reliable_event_date(value):
    """Return a calendar event date without inventing a clock time."""

    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None

    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _utc_now(now=None):
    value = now or datetime.now(timezone.utc)
    normalized = reliable_datetime(value)
    if normalized is None:
        raise ValueError("now must be timezone-aware")
    return normalized
