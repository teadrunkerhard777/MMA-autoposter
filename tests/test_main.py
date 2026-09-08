import pytest

import main
from main import _print_dry_run_diagnostics, load_article_data


def test_one_html_request_uses_source_config_for_text_and_image(monkeypatch):
    calls = []
    html = """
    <article><p>Article body</p></article>
    <meta property='og:image' content='/photo.jpg'>
    """

    def fetch(url, source_config=None):
        calls.append((url, source_config))
        return html

    monkeypatch.setattr("main.fetch_article_html", fetch)
    source_config = {
        "name": "Example",
        "type": "html",
        "headers": {"User-Agent": "Browser UA"},
        "retries": 2,
    }
    item = {
        "title": "Story",
        "url": "https://example.test/story",
        "source": "Example",
    }

    load_article_data([item], sources=[source_config])

    assert calls == [("https://example.test/story", source_config)]
    assert item["article_text"] == "Article body"
    assert item["image_url"] == "https://example.test/photo.jpg"


def test_preloaded_article_data_skips_http(monkeypatch):
    monkeypatch.setattr("main.fetch_article_html", lambda url: pytest.fail("unexpected request"))
    item = {
        "url": "https://example.test/story",
        "article_text": "Already loaded",
        "image_url": None,
    }

    load_article_data([item])


def test_dry_run_diagnostics_show_rank_confirmation_and_selection(capsys):
    candidate = {
        "title": "Майкл Пейдж получил нового соперника",
        "source": "AllBoxing.ru MMA",
        "score": 18,
        "confirmed_sources": [
            "AllBoxing.ru MMA",
            "FightTime.ru",
            "Sports.ru UFC/MMA",
        ],
        "confirmation_bonus": 2,
    }

    _print_dry_run_diagnostics([candidate], [candidate])

    output = capsys.readouterr().out
    assert "[TOP CANDIDATES]" in output
    assert "1. score=18 | source=AllBoxing.ru MMA | confirmed=3" in output
    assert (
        "confirmed_sources=AllBoxing.ru MMA,FightTime.ru,Sports.ru UFC/MMA"
    ) in output
    assert "confirmation_bonus=2" in output
    assert "[SELECTED]" in output


def test_run_applies_editorial_selection_after_event_dedup(monkeypatch):
    first = {"title": "First", "url": "https://example.test/first"}
    second = {"title": "Second", "url": "https://example.test/second"}
    ranked = [first, second]
    settings = {"enabled": True, "min_shared_tokens": 4}
    stages = []
    selection_call = {}

    monkeypatch.setattr(main, "configure_ssl", lambda: None)
    monkeypatch.setattr(main, "collect_enabled_news", lambda: ranked)
    monkeypatch.setattr(
        main,
        "filter_time_eligible",
        lambda items, days: items,
    )
    monkeypatch.setattr(main, "filter_relevant", lambda items, rule: items)
    monkeypatch.setattr(main, "add_scores", lambda items, scorer: None)
    monkeypatch.setattr(
        main,
        "filter_by_minimum_score",
        lambda items, minimum: items,
    )
    monkeypatch.setattr(main, "sort_by_score", lambda items: items)
    monkeypatch.setattr(main, "load_article_data", lambda items: None)

    def deduplicate(items, event_settings, debug=False):
        stages.append("dedup")
        return items

    def select(items, limit, diversity_settings, evergreen_slots):
        stages.append("selection")
        selection_call.update(
            items=items,
            limit=limit,
            settings=diversity_settings,
            evergreen_slots=evergreen_slots,
        )
        return [second]

    monkeypatch.setattr(main, "remove_duplicates", deduplicate)
    monkeypatch.setattr(main, "select_editorial_mix", select)
    monkeypatch.setattr(main, "load_history", lambda: [])
    monkeypatch.setattr(main, "publish_selected_news", lambda *args: False)
    monkeypatch.setattr(main, "DRY_RUN", True)
    monkeypatch.setattr(main, "MAX_NEWS_PER_RUN", 2)
    monkeypatch.setattr(main, "EVERGREEN_SLOTS_PER_RUN", 1)
    monkeypatch.setattr(main, "DIVERSITY_SETTINGS", settings)

    selected = main.run()

    assert stages == ["dedup", "selection"]
    assert selection_call == {
        "items": ranked,
        "limit": 2,
        "settings": settings,
        "evergreen_slots": 1,
    }
    assert selected == [second]
