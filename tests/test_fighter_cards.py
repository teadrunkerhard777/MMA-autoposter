import json
from pathlib import Path

from project.fighter_cards import (
    FIGHTERS_ROOT,
    load_fighter_cards,
    validate_fighter_card,
)


def test_fighter_base_contains_30_valid_unique_cards():
    cards = load_fighter_cards()

    assert len(cards) == 30
    assert len({card["id"] for card in cards}) == 30
    assert sum(card["gender"] == "male" for card in cards) == 15
    assert sum(card["gender"] == "female" for card in cards) == 15
    assert all(validate_fighter_card(card) == [] for card in cards)


def test_initial_order_alternates_men_and_women():
    cards = load_fighter_cards()

    assert [card["gender"] for card in cards] == ["male", "female"] * 15


def test_index_ids_match_card_directories_and_card_ids():
    index = json.loads((FIGHTERS_ROOT / "index.json").read_text(encoding="utf-8"))
    card_dirs = {
        path.parent.name
        for path in FIGHTERS_ROOT.glob("*/card.json")
    }

    assert set(index["rotation_order"]) == card_dirs
    assert all(
        card["id"] == fighter_id
        for fighter_id, card in zip(index["rotation_order"], load_fighter_cards())
    )


def test_sources_stay_internal_and_images_are_not_falsely_cleared():
    for card in load_fighter_cards():
        assert "post" not in card
        assert all(source["url"].startswith("https://") for source in card["sources"])
        assert card["image"]["publication_ready"] is False
        assert card["image"]["rights_status"] == "pending"
        assert not (Path(FIGHTERS_ROOT.parent.parent.parent) / card["image"]["local_path"]).exists()
