"""Load and validate the project-specific Fighter of the Day content base."""

from __future__ import annotations

import json
from pathlib import Path


FIGHTERS_ROOT = Path(__file__).parent / "content" / "fighters"
REQUIRED_TITLE_GROUPS = {"current", "former", "other"}


def load_fighter_cards(root: Path = FIGHTERS_ROOT) -> list[dict]:
    """Return fighter cards in the editorial order declared by index.json."""
    index = json.loads((root / "index.json").read_text(encoding="utf-8"))
    cards = []
    for fighter_id in index["rotation_order"]:
        card_path = root / fighter_id / "card.json"
        cards.append(json.loads(card_path.read_text(encoding="utf-8")))
    return cards


def validate_fighter_card(card: dict) -> list[str]:
    """Return human-readable validation errors without mutating the card."""
    errors = []
    required = {
        "schema_version",
        "id",
        "name_ru",
        "name_en",
        "gender",
        "country",
        "promotion",
        "weight_class",
        "positioning",
        "career_story",
        "fighting_style",
        "titles",
        "achievements",
        "distinctive_features",
        "stats",
        "facts",
        "angles",
        "sources",
        "image",
        "last_posted_at",
        "enabled",
    }
    missing = sorted(required - card.keys())
    if missing:
        errors.append(f"missing fields: {', '.join(missing)}")
        return errors

    if card["gender"] not in {"male", "female"}:
        errors.append("gender must be male or female")
    if set(card["titles"]) != REQUIRED_TITLE_GROUPS:
        errors.append("titles must contain current, former and other groups")
    if not 5 <= len(card["facts"]) <= 10:
        errors.append("facts must contain from 5 to 10 entries")
    if len(card["angles"]) < 3:
        errors.append("angles must contain at least 3 entries")
    if not card["sources"]:
        errors.append("sources must not be empty")

    source_ids = {source.get("id") for source in card["sources"]}
    if None in source_ids or len(source_ids) != len(card["sources"]):
        errors.append("source ids must be present and unique")
    for source in card["sources"]:
        if not source.get("url", "").startswith("https://"):
            errors.append("source URLs must use HTTPS")

    fact_ids = {fact.get("id") for fact in card["facts"]}
    if None in fact_ids or len(fact_ids) != len(card["facts"]):
        errors.append("fact ids must be present and unique")
    for fact in card["facts"]:
        if not set(fact.get("source_ids", [])) <= source_ids:
            errors.append(f"unknown source in fact {fact.get('id')}")
    for angle in card["angles"]:
        if not set(angle.get("fact_ids", [])) <= fact_ids:
            errors.append(f"unknown fact in angle {angle.get('id')}")
    for title_group in card["titles"].values():
        for title in title_group:
            if not set(title.get("source_ids", [])) <= source_ids:
                errors.append(f"unknown source in title {title.get('name_ru')}")

    record = card["stats"].get("record", {})
    wins_by = card["stats"].get("wins_by", {})
    method_total = sum(wins_by.get(key, 0) for key in ("ko_tko", "submission", "decision"))
    if method_total != record.get("wins"):
        errors.append("wins_by total must match record wins")
    if not card["stats"].get("verified_at"):
        errors.append("stats.verified_at must not be empty")

    image = card["image"]
    image_required = {
        "local_path",
        "source_page",
        "creator",
        "license",
        "rights_status",
        "publication_ready",
    }
    image_missing = sorted(image_required - image.keys())
    if image_missing:
        errors.append(f"image missing fields: {', '.join(image_missing)}")
    if image.get("publication_ready") and image.get("rights_status") != "cleared_no_public_credit":
        errors.append("publication-ready image rights must allow use without public credit")

    return errors
