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
    no_credit_ids = {
        "alex_pereira",
        "charles_oliveira",
        "ilia_topuria",
        "justin_gaethje",
        "merab_dvalishvili",
        "valentina_shevchenko",
    }
    attributed_ids = {
        "alexa_grasso",
        "alexander_volkanovski",
        "arman_tsarukyan",
        "islam_makhachev",
        "kayla_harrison",
        "khamzat_chimaev",
        "mackenzie_dern",
        "manon_fiorot",
        "natalia_silva",
        "petr_yan",
        "rose_namajunas",
        "salahdine_parnasse",
        "sean_strickland",
        "tatiana_suarez",
        "tracy_cortez",
        "umar_nurmagomedov",
        "zhang_weili",
    }
    for card in load_fighter_cards():
        assert "post" not in card
        assert all(source["url"].startswith("https://") for source in card["sources"])
        image_path = Path(FIGHTERS_ROOT.parent.parent.parent) / card["image"]["local_path"]
        if card["id"] in no_credit_ids:
            assert card["image"]["publication_ready"] is True
            assert card["image"]["rights_status"] == "cleared_no_public_credit"
            assert card["image"]["source_page"].startswith("https://commons.wikimedia.org/")
            assert image_path.is_file()
        elif card["id"] in attributed_ids:
            assert card["image"]["publication_ready"] is True
            assert card["image"]["rights_status"] == "cleared_with_embedded_attribution"
            assert card["image"]["source_page"].startswith("https://commons.wikimedia.org/")
            assert card["image"]["license"].startswith("CC BY")
            assert image_path.is_file()
        else:
            assert card["image"]["publication_ready"] is False
            assert card["image"]["rights_status"] == "pending"
            assert not image_path.exists()
