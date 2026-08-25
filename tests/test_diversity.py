from processing.deduplicator import remove_duplicates
from processing.diversity import select_diverse
from project.settings import DIVERSITY_SETTINGS


def make_item(title, body, category, source="example"):
    slug = title.casefold().replace(" ", "-")
    return {
        "title": title,
        "description": "",
        "article_text": body,
        "event_category": category,
        "matched_topics": [category],
        "source": source,
        "url": f"https://{source}.test/{slug}",
    }


def similar_cluster():
    first = make_item(
        "Executive publishes accusations",
        "founder partner contract payment lawsuit dispute private messages",
        "business",
    )
    second = make_item(
        "Contract response follows",
        "partner founder contract lawsuit dispute payments message response",
        "business",
    )
    return first, second


def distinct_items():
    return [
        make_item(
            "Space telescope captures a distant galaxy",
            "astronomers observe stars orbit light cosmic image",
            "science",
        ),
        make_item(
            "Central bank changes its interest rate",
            "economy inflation lending monetary policy markets",
            "finance",
        ),
        make_item(
            "Football coach leaves the city club",
            "team season players stadium training championship",
            "sports",
        ),
    ]


def test_diverse_topics_preserve_ranked_order():
    items = distinct_items()

    assert select_diverse(items, 2, DIVERSITY_SETTINGS) == items[:2]


def test_very_similar_stories_are_not_selected_together():
    first, second = similar_cluster()

    assert select_diverse(
        [first, second],
        2,
        DIVERSITY_SETTINGS,
    ) == [first]


def test_next_diverse_candidate_replaces_skipped_story():
    first, similar = similar_cluster()
    diverse = distinct_items()[0]

    assert select_diverse(
        [first, similar, diverse],
        2,
        DIVERSITY_SETTINGS,
    ) == [first, diverse]


def test_selection_returns_all_available_distinct_candidates():
    items = distinct_items()[:2]

    assert select_diverse(items, 5, DIVERSITY_SETTINGS) == items


def test_limit_one_preserves_top_ranked_item():
    items = distinct_items()

    assert select_diverse(items, 1, DIVERSITY_SETTINGS) == [items[0]]


def test_disabled_or_missing_settings_preserve_top_n():
    first, similar = similar_cluster()
    items = [first, similar]

    assert select_diverse(items, 2, {"enabled": False}) == items
    assert select_diverse(items, 2, None) == items


def test_event_dedup_and_diversity_are_separate_stages():
    first, similar = similar_cluster()

    assert remove_duplicates([first, similar]) == [first, similar]
    assert select_diverse(
        [first, similar],
        2,
        DIVERSITY_SETTINGS,
    ) == [first]
