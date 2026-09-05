from datetime import datetime, timezone

from project.events import enrich_event_timing


PUBLISHED_AT = datetime(2026, 9, 5, 9, tzinfo=timezone.utc)


def news(category, text):
    return {
        "title": "UFC проведёт турнир",
        "description": "",
        "article_text": text,
        "published_at": PUBLISHED_AT,
        "event_category": category,
    }


def test_explicit_russian_date_and_moscow_time_become_event_at():
    item = news(
        "event_update",
        (
            "5 сентября в Париже пройдет турнир UFC. "
            "Основной кард начнется в 22:00 по московскому времени."
        ),
    )

    enrich_event_timing(item)

    assert item["event_date"] == "2026-09-05"
    assert item["event_at"].isoformat() == "2026-09-05T22:00:00+03:00"
    assert item["event_date_precision"] == "minute"
    assert item["event_date_source"] == "article_explicit"


def test_explicit_date_without_time_stays_a_calendar_date():
    item = news(
        "fight_announcement",
        "Бой состоится 10 сентября, точное время объявят позднее.",
    )

    enrich_event_timing(item)

    assert item["event_date"] == "2026-09-10"
    assert item["event_date_precision"] == "date"
    assert "event_at" not in item


def test_recent_result_can_use_previous_day_as_event_date():
    item = news(
        "fight_result",
        "Турнир прошел в пятницу, 4 сентября.",
    )

    enrich_event_timing(item)

    assert item["event_date"] == "2026-09-04"


def test_non_event_story_does_not_turn_historical_dates_into_event_time():
    item = news(
        "contract_move",
        "Боец выступал в апреле 2018 года и подписал контракт сегодня.",
    )

    enrich_event_timing(item)

    assert "event_date" not in item
    assert "event_at" not in item


def test_invalid_calendar_date_is_ignored():
    item = news(
        "event_update",
        "Турнир пройдет 31 февраля.",
    )

    enrich_event_timing(item)

    assert "event_date" not in item
