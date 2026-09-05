from copy import deepcopy
from datetime import datetime, timezone

from project.fighter_cards import load_fighter_cards
from project.fighter_of_day import (
    format_fighter_post,
    select_next_fighter,
    simulate_fighter_days,
)


NOW = datetime(2026, 9, 6, 9, 0, tzinfo=timezone.utc)
MISSING_IMAGE_IDS = {
    "denise_gomes",
    "erin_blanchfield",
    "fatima_kline",
    "maycee_barber",
    "song_yadong",
    "tom_aspinall",
    "yan_xiaonan",
}


def test_selects_first_eligible_fighter():
    selected = select_next_fighter(load_fighter_cards(), [], NOW)

    assert selected["fighter_id"] == "islam_makhachev"
    assert selected["cycle"] == 1
    assert selected["fallback_used"] is False


def test_alternates_male_and_female_when_both_are_available():
    results = simulate_fighter_days(10, start_at=NOW)

    assert [item["gender"] for item in results] == ["male", "female"] * 5


def test_has_no_repeats_inside_a_cycle():
    results = simulate_fighter_days(23, start_at=NOW)

    assert len({item["fighter_id"] for item in results}) == 23
    assert not any(item["repeated"] for item in results)


def test_skips_all_cards_without_images_without_error():
    results = simulate_fighter_days(30, start_at=NOW)

    assert MISSING_IMAGE_IDS.isdisjoint(item["fighter_id"] for item in results)


def test_skips_card_with_invalid_license():
    cards = deepcopy(load_fighter_cards())
    cards[0]["image"]["rights_status"] = "unverified"

    selected = select_next_fighter(cards, [], NOW)

    assert selected["fighter_id"] != "islam_makhachev"


def test_falls_back_to_other_gender_when_preferred_gender_is_unavailable():
    cards = [card for card in load_fighter_cards() if card["gender"] == "male"]
    history = [{
        "kind": "fighter_of_day",
        "fighter_id": "previous",
        "selected_at": NOW.isoformat(),
        "cycle": 1,
        "content_topic": "angle_1",
        "gender": "male",
    }]

    selected = select_next_fighter(cards, history, NOW)

    assert selected["gender"] == "male"
    assert selected["fallback_used"] is True


def test_starts_new_cycle_after_all_available_fighters_are_used():
    results = simulate_fighter_days(24, start_at=NOW)

    assert results[22]["cycle"] == 1
    assert results[23]["cycle"] == 2
    assert results[23]["started_new_cycle"] is True


def test_rotation_works_with_only_one_gender():
    cards = [card for card in load_fighter_cards() if card["gender"] == "female"]
    results = simulate_fighter_days(5, cards=cards, start_at=NOW)

    assert len(results) == 5
    assert all(item["gender"] == "female" for item in results)
    assert len({item["fighter_id"] for item in results}) == 5


def test_empty_candidate_list_stops_cleanly():
    assert simulate_fighter_days(5, cards=[], start_at=NOW) == []


def test_dry_run_does_not_change_production_history():
    history = [{"title": "production entry", "url": "https://example.test/news"}]
    original = deepcopy(history)

    simulate_fighter_days(15, production_history=history, start_at=NOW)

    assert history == original


def test_selection_is_reproducible():
    first = simulate_fighter_days(15, start_at=NOW)
    second = simulate_fighter_days(15, start_at=NOW)

    assert [item["fighter_id"] for item in first] == [
        item["fighter_id"] for item in second
    ]


def test_post_uses_compact_format_and_keeps_sources_private():
    selected = select_next_fighter(load_fighter_cards(), [], NOW)
    post = format_fighter_post(selected["card"], selected["content_topic"])

    assert "БОЕЦ ДНЯ" in post
    assert "📊" in post
    assert "🏆" in post
    assert "⚡" in post
    assert "Интересный факт" in post
    assert "https://" not in post
    assert "Источник" not in post
    assert len(post) <= 1000
