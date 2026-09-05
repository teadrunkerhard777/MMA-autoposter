from datetime import datetime, timedelta, timezone

from storage.history import add_to_history, is_published, load_history, save_history


def news(url="https://example.test/story"):
    return {
        "title": "Python package release",
        "url": url,
        "source": "Example",
        "published_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "description": "package release testing runner plugin benchmark community",
        "event_category": "python",
    }


def test_empty_history_round_trip(tmp_path):
    path = tmp_path / "published.json"
    save_history([], path)
    assert load_history(path) == []


def test_new_history_entry_contains_compact_fingerprint():
    history = []
    item = news()
    item.update(
        event_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
        event_date="2026-02-01",
        event_participants=["fighter_a", "fighter_b"],
    )
    add_to_history(item, history)

    assert history[0]["event_fingerprint"]["categories"] == ["python"]
    assert history[0]["event_fingerprint"]["event_at"] == (
        "2026-02-01T00:00:00+00:00"
    )
    assert history[0]["event_fingerprint"]["event_date"] == "2026-02-01"
    assert history[0]["event_fingerprint"]["participants"] == [
        "fighter_a",
        "fighter_b",
    ]
    assert "article_text" not in history[0]


def test_legacy_history_without_fingerprint_remains_url_compatible():
    item = news()
    assert is_published(item, [{"url": item["url"]}]) is True
    assert is_published(item, [{"url": "https://other.test"}]) is False


def test_history_matches_old_republication_by_reliable_event_identity():
    original = news("https://first.test/fight")
    original.update(
        event_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        event_participants=["fighter_a", "fighter_b"],
    )
    history = []
    add_to_history(original, history)
    repeated = {
        **original,
        "url": "https://second.test/fight",
        "source": "Other",
        "published_at": original["published_at"] + timedelta(days=300),
    }

    assert is_published(repeated, history) is True


def test_history_url_match_ignores_tracking_parameters():
    item = news("https://example.test/story?utm_source=telegram")
    history = [{"url": "https://example.test/story#comments"}]

    assert is_published(item, history) is True
