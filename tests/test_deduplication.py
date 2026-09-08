from datetime import datetime, timedelta, timezone

from processing.deduplicator import (
    compare_event_fingerprints,
    normalize_url,
    remove_duplicates,
    titles_are_similar,
)
from project.settings import EVENT_DEDUP_SETTINGS
from project.scoring import calculate_score


NOW = datetime(2026, 1, 2, tzinfo=timezone.utc)


def make_item(source, title, body, category="release", hours=0, url=None):
    return {
        "source": source,
        "title": title,
        "url": url or f"https://{source}.test/{hours}",
        "published_at": NOW + timedelta(hours=hours),
        "article_text": body,
        "event_category": category,
        "event_locations": [],
        "score": 3,
    }


def test_regular_url_and_title_deduplication():
    first = make_item("a", "Python project ships version 4", "one", url="https://same")
    same_url = make_item("b", "Different title", "two", url="https://same")
    same_title = make_item("c", "Python project ships version 4", "three")

    assert remove_duplicates([first, same_url, same_title]) == [first]


def test_tracking_parameters_and_fragments_do_not_create_new_urls():
    first = make_item(
        "a",
        "First report",
        "body",
        url="https://News.test/story/?id=42&utm_source=telegram#top",
    )
    repeated = make_item(
        "b",
        "Different title",
        "other",
        url="https://news.test/story?id=42&utm_medium=social",
    )

    assert normalize_url(first["url"]) == "https://news.test/story?id=42"
    assert remove_duplicates([first, repeated]) == [first]


def test_cross_source_event_duplicate_is_merged():
    facts = "python maintainers release faster runner plugin benchmark community package"
    first = make_item("a", "New Python runner released", facts)
    second = make_item("b", "Community ships runner update", facts, hours=2)

    details = compare_event_fingerprints(first, second, EVENT_DEDUP_SETTINGS)

    assert details["is_duplicate"] is True
    assert len(remove_duplicates([first, second], EVENT_DEDUP_SETTINGS)) == 1


def test_deduplicated_story_keeps_unique_confirming_sources():
    facts = "python maintainers release faster runner plugin benchmark community package"
    first = make_item("Sports.ru UFC/MMA", "New Python runner released", facts)
    second = make_item("FightTime.ru", "Community ships runner update", facts, hours=2)
    third = make_item("AllBoxing.ru MMA", "Runner update confirmed", facts, hours=3)
    fourth = make_item("FightTime.ru", "Runner update confirmed again", facts, hours=4)

    merged = remove_duplicates(
        [first, second, third, fourth],
        EVENT_DEDUP_SETTINGS,
    )

    assert len(merged) == 1
    assert merged[0]["confirmed_sources"] == [
        "Sports.ru UFC/MMA",
        "FightTime.ru",
        "AllBoxing.ru MMA",
    ]


def test_confirmation_bonus_is_capped_for_independent_sources():
    item = {
        "source": "Sports.ru UFC/MMA",
        "event_category": "fighter_news",
        "matched_promotions": [],
        "editorial_signals": [],
        "matched_fighters": [],
        "is_rumor": False,
    }

    assert calculate_score(item, now=NOW) == item["score_before_confirmation"]
    assert item["confirmation_bonus"] == 0

    item["confirmed_sources"] = ["Sports.ru UFC/MMA", "FightTime.ru"]
    assert calculate_score(item, now=NOW) == item["score_before_confirmation"] + 1
    assert item["confirmation_bonus"] == 1

    item["confirmed_sources"] = [
        "Sports.ru UFC/MMA",
        "FightTime.ru",
        "AllBoxing.ru MMA",
    ]
    assert calculate_score(item, now=NOW) == item["score_before_confirmation"] + 2
    assert item["confirmation_bonus"] == 2

    item["confirmed_sources"].append("Fourth source")
    assert calculate_score(item, now=NOW) == item["score_before_confirmation"] + 2
    assert item["confirmation_bonus"] == 2


def test_close_but_different_events_are_not_merged():
    first = make_item(
        "a", "Python formatter update", "formatter syntax output terminal colors"
    )
    second = make_item(
        "b", "Python database update", "database index storage query optimizer", hours=2
    )

    assert compare_event_fingerprints(first, second, EVENT_DEDUP_SETTINGS)["is_duplicate"] is False


def test_different_categories_are_not_merged_even_with_same_text():
    body = "shared detailed tokens alpha beta gamma delta epsilon zeta"
    first = make_item("a", "Tool release", body, category="release")
    second = make_item("b", "Tool advisory", body, category="security", hours=1)

    assert compare_event_fingerprints(first, second, EVENT_DEDUP_SETTINGS)["is_duplicate"] is False


def test_optional_location_can_support_event_match():
    body = "maintainers publish package benchmark runner plugin"
    first = make_item("a", "Tool update", body)
    second = make_item("b", "Package update", body, hours=1)
    first["event_locations"] = ["Berlin"]
    second["event_locations"] = ["Berlin"]

    assert compare_event_fingerprints(first, second, EVENT_DEDUP_SETTINGS)["is_duplicate"] is True


def test_same_fight_matches_across_languages_by_participants_and_event_time():
    first = make_item(
        "one",
        "Царукян победил Руффи",
        "Результат поединка в Париже",
        category="fight_result",
    )
    second = make_item(
        "two",
        "Tsarukyan defeats Ruffy",
        "Fight result from Paris",
        category="fight_result",
        hours=24 * 30,
    )
    event_at = NOW + timedelta(days=3)
    first.update(
        event_at=event_at,
        event_participants=["arman_tsarukyan", "mauricio_ruffy"],
    )
    second.update(
        event_at=event_at,
        event_participants=["mauricio_ruffy", "arman_tsarukyan"],
    )

    details = compare_event_fingerprints(first, second, EVENT_DEDUP_SETTINGS)

    assert details["is_duplicate"] is True
    assert details["shared_participants"] == [
        "arman_tsarukyan",
        "mauricio_ruffy",
    ]


def test_different_fights_in_same_promotion_are_not_merged():
    shared = "UFC tournament title fight main card result official"
    first = make_item(
        "one",
        "UFC Paris main card: Fighter A vs Fighter B result",
        shared,
        category="fight_result",
    )
    second = make_item(
        "two",
        "UFC Paris main card: Fighter C vs Fighter D result",
        shared,
        category="fight_result",
        hours=1,
    )
    first["event_participants"] = ["fighter_a", "fighter_b"]
    second["event_participants"] = ["fighter_c", "fighter_d"]

    assert titles_are_similar(first["title"], second["title"])
    assert compare_event_fingerprints(
        first,
        second,
        EVENT_DEDUP_SETTINGS,
    )["is_duplicate"] is False
    assert remove_duplicates([first, second], EVENT_DEDUP_SETTINGS) == [
        first,
        second,
    ]


def test_different_reliable_event_dates_keep_rematches_separate():
    shared = "UFC title fight first fighter second fighter official result"
    first = make_item("one", "First fight", shared, category="fight_result")
    second = make_item("two", "Rematch", shared, category="fight_result", hours=1)
    first.update(
        event_at=NOW,
        event_participants=["fighter_a", "fighter_b"],
    )
    second.update(
        event_at=NOW + timedelta(days=90),
        event_participants=["fighter_a", "fighter_b"],
    )

    assert compare_event_fingerprints(
        first,
        second,
        EVENT_DEDUP_SETTINGS,
    )["is_duplicate"] is False


def test_timezone_naive_event_date_cannot_bypass_publication_window():
    first = make_item(
        "one",
        "Царукян против Руффи",
        "Первый материал",
        category="fight_announcement",
    )
    second = make_item(
        "two",
        "Tsarukyan versus Ruffy",
        "Second report",
        category="fight_announcement",
        hours=24 * 30,
    )
    for item in (first, second):
        item.update(
            event_at=datetime(2026, 2, 1),
            event_participants=["arman_tsarukyan", "mauricio_ruffy"],
        )

    assert compare_event_fingerprints(
        first,
        second,
        EVENT_DEDUP_SETTINGS,
    )["is_duplicate"] is False


def test_same_explicit_event_date_matches_beyond_publication_window():
    first = make_item(
        "one",
        "Царукян против Руффи",
        "Первый материал",
        category="fight_announcement",
    )
    second = make_item(
        "two",
        "Tsarukyan versus Ruffy",
        "Second report",
        category="fight_announcement",
        hours=24 * 30,
    )
    for item in (first, second):
        item.update(
            event_date="2026-02-01",
            event_participants=["arman_tsarukyan", "mauricio_ruffy"],
        )

    assert compare_event_fingerprints(
        first,
        second,
        EVENT_DEDUP_SETTINGS,
    )["is_duplicate"] is True
