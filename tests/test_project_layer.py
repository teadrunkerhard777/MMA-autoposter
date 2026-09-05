from datetime import datetime, timezone

from processing.filters import (
    add_scores,
    filter_by_minimum_score,
    filter_relevant,
)
from project.filters import is_relevant
from project.formatter import format_photo_caption, format_post
from project.scoring import calculate_score
from project.settings import (
    EVERGREEN_SLOTS_PER_RUN,
    MAX_NEWS_PER_RUN,
    MIN_PUBLICATION_SCORE,
)
from project.sources import SOURCES


def item(title, description=""):
    return {
        "title": title,
        "description": description,
        "url": "https://example.test/item?a=1&b=2",
        "source": "MMA <Test>",
        "published_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
    }


def test_project_filter_accepts_mma_and_rejects_unrelated_sport():
    accepted = item("UFC официально объявил новый титульный бой")
    rejected = item("Футбольный клуб объявил нового тренера")

    assert filter_relevant([accepted, rejected], is_relevant) == [accepted]
    assert accepted["event_category"] == "fight_announcement"
    assert accepted["matched_promotions"] == ["ufc"]
    assert rejected["matched_topics"] == []
    assert rejected["event_category"] is None


def test_priority_fighter_needs_fight_context_without_an_mma_promotion():
    relevant = item("Пётр Ян назвал следующего соперника")
    unrelated = item("Конор Макгрегор представил новую коллекцию одежды")

    assert is_relevant(relevant) is True
    assert relevant["matched_fighters"] == ["petr_yan"]
    assert is_relevant(unrelated) is False


def test_mma_acronyms_do_not_match_inside_unrelated_words():
    russian = item("Городская программа поддержки спорта")
    english = item("Vacation plans for the summer")

    assert is_relevant(russian) is False
    assert is_relevant(english) is False


def test_project_assigns_meaningful_event_categories():
    injured = item("Боец UFC снялся с турнира из-за травмы")
    result = item("Боец ACA победил нокаутом в главном бою")

    assert is_relevant(injured) is True
    assert injured["event_category"] == "injury"
    assert is_relevant(result) is True
    assert result["event_category"] == "fight_result"


def test_rumor_is_attached_as_separate_editorial_metadata():
    news = item(
        "Хамзат Чимаев может получить нового соперника",
        "По данным журналиста, UFC ведёт переговоры о бое.",
    )

    assert is_relevant(news) is True
    assert news["is_rumor"] is True
    assert news["content_type"] == "rumor"
    assert "rumor" in news["matched_topics"]
    assert "official" not in news["editorial_signals"]


def test_major_confirmed_story_scores_above_rumor_and_threshold():
    confirmed = item(
        "UFC официально объявил титульный бой Ислама Махачева"
    )
    rumor = item(
        "Ислам Махачев может получить соперника",
        "По данным журналиста, UFC ведёт переговоры о бое.",
    )

    news = [confirmed, rumor]
    filter_relevant(news, is_relevant)
    add_scores(news, calculate_score)

    assert confirmed["score"] > rumor["score"]
    assert filter_by_minimum_score(news, MIN_PUBLICATION_SCORE) == news


def test_formatter_escapes_html_and_keeps_russian_source_footer():
    news = item("UFC объявил бой <чемпиона>", "Сильный & важный поединок")
    is_relevant(news)

    post = format_post(news)

    assert "&lt;чемпиона&gt;" in post
    assert "Сильный &amp; важный поединок" in post
    assert "MMA &lt;Test&gt;" in post
    assert 'href="https://example.test/item?a=1&amp;b=2"' in post
    assert ">Источник</a>" in post


def test_rumor_formatter_never_presents_unconfirmed_item_without_warning():
    news = item(
        "Хамзат Чимаев может получить соперника",
        "По данным журналиста, UFC ведёт переговоры о бое.",
    )
    is_relevant(news)

    post = format_post(news)

    assert "<b>СЛУХ</b>" in post
    assert "Пока официально не подтверждено." in post
    assert "#Слух" in post


def test_photo_caption_stays_inside_safe_limit_after_html_escaping():
    news = item("UFC объявил новый бой", "<&> word " * 1000)
    is_relevant(news)

    assert len(format_photo_caption(news)) <= 1000


def test_stage_three_keeps_only_local_source_enabled_before_extraction_review():
    enabled = [source for source in SOURCES if source["enabled"]]
    candidates = [source for source in SOURCES if not source["enabled"]]

    assert len(enabled) == 1
    assert enabled[0]["type"] == "static"
    assert all(source["type"] == "rss" for source in candidates)
    assert all(source["limit"] > 0 for source in candidates)
    assert {source["language"] for source in candidates} == {"en", "ru"}
    assert MAX_NEWS_PER_RUN == 5
    assert EVERGREEN_SLOTS_PER_RUN == 2


def test_evergreen_content_gets_its_own_category_and_format():
    profile = item("Женщины в MMA: яркий профиль спортсменки")
    profile.update(
        content_queue="evergreen",
        content_type="women_mma",
        scheduled_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    assert is_relevant(profile) is True
    assert profile["event_category"] == "evergreen_women_mma"
    assert "✨ ЖЕНЩИНЫ В MMA" in format_post(profile)
