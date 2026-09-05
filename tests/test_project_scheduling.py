from datetime import datetime, timedelta, timezone

from processing.filters import sort_by_score
from project.filters import is_relevant
from project.scoring import calculate_score
from project.scheduling import event_window, filter_time_eligible
from project.selection import select_editorial_mix, sort_by_editorial_priority


NOW = datetime(2026, 9, 5, 12, tzinfo=timezone.utc)


def news(title="UFC объявил новый бой", **values):
    return {
        "title": title,
        "description": "UFC проведёт турнир",
        "url": f"https://example.test/{id(values)}",
        "source": "Test",
        "published_at": NOW - timedelta(hours=1),
        **values,
    }


def evergreen(name, scheduled_at):
    return news(
        f"Профиль бойца MMA: {name}",
        content_queue="evergreen",
        content_type="fighter",
        scheduled_at=scheduled_at,
    )


def score(item):
    assert is_relevant(item) is True
    item["score"] = calculate_score(item, now=NOW)
    return item


def test_event_window_uses_only_reliable_timezone_aware_dates():
    assert event_window(NOW + timedelta(hours=48), NOW) == "next_48_hours"
    assert event_window(NOW + timedelta(days=7), NOW) == "next_7_days"
    assert event_window(NOW + timedelta(days=8), NOW) == "later"
    assert event_window(NOW - timedelta(minutes=1), NOW) == "past"
    assert event_window(datetime(2026, 9, 6), NOW) is None
    assert event_window(None, NOW) is None


def test_event_window_uses_explicit_date_without_inventing_time():
    assert event_window(None, NOW, "2026-09-07") == "next_48_hours"
    assert event_window(None, NOW, "2026-09-10") == "next_7_days"
    assert event_window(None, NOW, "2026-09-13") == "later"
    assert event_window(None, NOW, "not-a-date") is None


def test_time_filter_keeps_fresh_news_and_only_due_evergreen_items():
    fresh = news("Свежая новость UFC")
    old = news(
        "Старая новость UFC",
        published_at=NOW - timedelta(days=10),
    )
    ready = evergreen("готов", NOW - timedelta(minutes=1))
    future = evergreen("позже", NOW + timedelta(minutes=1))
    unscheduled = evergreen("без времени", None)

    assert filter_time_eligible(
        [fresh, old, ready, future, unscheduled],
        lookback_days=3,
        now=NOW,
    ) == [fresh, ready]


def test_old_event_is_not_made_fresh_by_a_new_article_date():
    republished = news(
        "Новый материал о старом турнире UFC",
        published_at=NOW - timedelta(hours=1),
        event_at=NOW - timedelta(days=30),
    )

    assert filter_time_eligible(
        [republished],
        lookback_days=3,
        now=NOW,
    ) == []


def test_recent_result_with_reliable_event_date_remains_eligible():
    result = news(
        "Результат вчерашнего турнира UFC",
        event_at=NOW - timedelta(days=1),
    )

    assert filter_time_eligible(
        [result],
        lookback_days=3,
        now=NOW,
    ) == [result]


def test_old_calendar_event_date_is_stale_without_invented_time():
    republished = news(
        "Новая статья о старом турнире UFC",
        event_date="2026-08-01",
    )

    assert filter_time_eligible(
        [republished],
        lookback_days=3,
        now=NOW,
    ) == []


def test_next_48_hour_event_scores_above_comparable_week_event():
    near = score(news(event_at=NOW + timedelta(hours=24)))
    week = score(news(event_at=NOW + timedelta(days=5)))

    assert near["event_window"] == "next_48_hours"
    assert week["event_window"] == "next_7_days"
    assert near["score"] > week["score"]


def test_breaking_injury_can_outrank_an_ordinary_near_preview():
    preview = score(news(event_at=NOW + timedelta(hours=24)))
    injury = score(
        news(
            "Травма изменила кард UFC",
            event_at=NOW + timedelta(days=5),
        )
    )

    assert injury["editorial_priority"] == "breaking"
    assert injury["score"] > preview["score"]


def test_editorial_priority_orders_events_before_scandal_and_routine_news():
    near = score(news(event_date="2026-09-06"))
    week = score(news(event_date="2026-09-10"))
    scandal = score(news("Боец UFC устроил скандал: «Это конфликт»"))
    routine = score(news("Боец UFC заявил: «Продолжаю тренировки»"))

    assert near["score"] > week["score"] > scandal["score"] > routine["score"]
    assert near["editorial_priority"] == "next_48_hours"
    assert week["editorial_priority"] == "next_7_days"
    assert scandal["editorial_priority"] == "major_story"


def test_editorial_tiers_cannot_be_overridden_by_star_bonus():
    near = score(news(event_date="2026-09-06"))
    week = score(news(event_date="2026-09-10"))
    loud_scandal = score(news(
        "Скандал UFC: Ислам Махачев вызвал Хамзата Чимаева",
    ))
    loud_scandal["score"] = 10_000

    assert sort_by_editorial_priority(
        [loud_scandal, week, near]
    ) == [near, week, loud_scandal]


def test_rumored_event_does_not_enter_confirmed_event_tiers():
    rumor = score(news(
        "По данным журналиста, UFC может объявить новый бой",
        event_date="2026-09-06",
    ))
    confirmed = score(news(event_date="2026-09-10"))

    assert rumor["is_rumor"] is True
    assert rumor["event_window"] == "next_48_hours"
    assert rumor["editorial_priority"] == "standard"
    assert sort_by_editorial_priority([rumor, confirmed]) == [
        confirmed,
        rumor,
    ]


def test_editorial_mix_reserves_two_due_evergreen_slots():
    reactive = [score(news(f"Новость UFC {index}")) for index in range(4)]
    scheduled = [
        score(evergreen("A", NOW - timedelta(hours=2))),
        score(evergreen("B", NOW - timedelta(hours=1))),
    ]
    ranked = sort_by_score(reactive + scheduled)

    selected = select_editorial_mix(
        ranked,
        limit=5,
        diversity_settings={"enabled": False},
        evergreen_slots=2,
    )

    assert len(selected) == 5
    assert sum(item.get("content_queue") == "evergreen" for item in selected) == 2


def test_five_priority_news_items_can_use_the_whole_batch():
    urgent = [
        score(news(f"Травма бойца UFC {index}"))
        for index in range(5)
    ]
    scheduled = [
        score(evergreen("A", NOW - timedelta(hours=2))),
        score(evergreen("B", NOW - timedelta(hours=1))),
    ]

    selected = select_editorial_mix(
        sort_by_score(urgent + scheduled),
        limit=5,
        diversity_settings={"enabled": False},
        evergreen_slots=2,
    )

    assert len(selected) == 5
    assert all(item.get("editorial_priority") == "breaking" for item in selected)
