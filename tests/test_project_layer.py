from datetime import datetime, timezone

from processing.filters import (
    add_scores,
    filter_by_minimum_score,
    filter_relevant,
)
from project.filters import is_relevant
from project.formatter import format_photo_caption, format_post
from project.scoring import calculate_score


def item(title, description=""):
    return {
        "title": title,
        "description": description,
        "url": "https://example.test/item",
        "source": "Example",
        "published_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
    }


def test_project_filter_accepts_technology_and_rejects_unrelated_news():
    accepted = item("Python gets a new testing tool")
    rejected = item("Council changes parking rules")

    assert filter_relevant([accepted, rejected], is_relevant) == [accepted]
    assert accepted["event_category"] == "python"
    assert rejected["matched_topics"] == []


def test_project_scoring_is_applied_by_generic_core():
    news = item("Python open-source test runner")
    is_relevant(news)
    add_scores([news], calculate_score)

    assert news["score"] == 6
    assert filter_by_minimum_score([news], 2) == [news]


def test_formatter_escapes_html_and_keeps_project_footer():
    news = item("Python <release>", "Safer & faster")
    news["matched_topics"] = ["python"]

    post = format_post(news)

    assert "Python &lt;release&gt;" in post
    assert "Safer &amp; faster" in post
    assert "#python" in post
    assert 'href="https://example.test/item"' in post


def test_photo_caption_stays_inside_safe_limit():
    news = item("Python release", "word " * 1000)
    news["matched_topics"] = ["python"]

    assert len(format_photo_caption(news)) <= 1000

