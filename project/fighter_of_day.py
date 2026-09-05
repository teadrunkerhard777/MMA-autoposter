"""Deterministic Fighter of the Day rotation and dry-run simulation."""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

from project.fighter_cards import (
    load_fighter_cards,
    validate_fighter_card,
    validate_fighter_image,
)


HISTORY_KIND = "fighter_of_day"
DEFAULT_GENDER = "male"


def eligible_fighters(cards: list[dict], project_root: Path | None = None) -> list[dict]:
    """Return enabled cards whose content and local image both validate."""
    return [
        card
        for card in cards
        if card.get("enabled")
        and not validate_fighter_card(card)
        and not validate_fighter_image(card, project_root)
    ]


def select_next_fighter(
    cards: list[dict],
    history: list[dict],
    selected_at: datetime,
    project_root: Path | None = None,
) -> dict | None:
    """Select one unused fighter while preserving alternation when possible."""
    available = eligible_fighters(cards, project_root)
    if not available:
        return None

    fighter_history = [entry for entry in history if entry.get("kind") == HISTORY_KIND]
    cycle = max((entry.get("cycle", 1) for entry in fighter_history), default=1)
    used = {
        entry.get("fighter_id")
        for entry in fighter_history
        if entry.get("cycle") == cycle
    }
    unused = [card for card in available if card["id"] not in used]
    started_new_cycle = not unused
    if started_new_cycle:
        cycle += 1
        unused = available

    last_gender = fighter_history[-1].get("gender") if fighter_history else None
    preferred_gender = "female" if last_gender == "male" else DEFAULT_GENDER
    if last_gender == "female":
        preferred_gender = "male"

    preferred = [card for card in unused if card["gender"] == preferred_gender]
    fallback_used = not preferred
    candidates = preferred or unused
    card = candidates[0]
    topic_id = _select_topic(card, fighter_history)
    history_entry = {
        "kind": HISTORY_KIND,
        "fighter_id": card["id"],
        "selected_at": selected_at.isoformat(),
        "cycle": cycle,
        "content_topic": topic_id,
        "gender": card["gender"],
    }
    return {
        "card": card,
        "fighter_id": card["id"],
        "gender": card["gender"],
        "image_path": card["image"]["local_path"],
        "image_valid": True,
        "cycle": cycle,
        "content_topic": topic_id,
        "fallback_used": fallback_used,
        "started_new_cycle": started_new_cycle,
        "history_entry": history_entry,
        "post_html": format_fighter_post(card, topic_id),
    }


def simulate_fighter_days(
    days: int,
    cards: list[dict] | None = None,
    production_history: list[dict] | None = None,
    start_at: datetime | None = None,
    project_root: Path | None = None,
) -> list[dict]:
    """Run consecutive selections against isolated in-memory history."""
    simulation_history = deepcopy(production_history or [])
    current_time = start_at or datetime.now(timezone.utc)
    results = []
    seen_by_cycle: dict[int, set[str]] = {}

    for day in range(1, days + 1):
        selected = select_next_fighter(
            cards if cards is not None else load_fighter_cards(),
            simulation_history,
            current_time + timedelta(days=day - 1),
            project_root,
        )
        if selected is None:
            break
        cycle_seen = seen_by_cycle.setdefault(selected["cycle"], set())
        selected["day"] = day
        selected["repeated"] = selected["fighter_id"] in cycle_seen
        cycle_seen.add(selected["fighter_id"])
        results.append(selected)
        simulation_history.append(selected["history_entry"])
    return results


def format_fighter_post(card: dict, topic_id: str | None = None) -> str:
    """Build the agreed compact Telegram HTML post without public data links."""
    stats = card["stats"]
    record = stats["record"]
    wins_by = stats["wins_by"]
    streak = stats.get("current_streak") or {}
    streak_text = _streak_text(streak)
    title_text = _title_or_rank(card)
    fact = _fact_for_topic(card, topic_id)
    career = card.get("career_story", [])[:1]
    style = card.get("fighting_style", [])[:1]

    blocks = [
        f"🥊 <b>БОЕЦ ДНЯ — {escape(card['name_ru'].upper())}</b>",
        (
            f"📊 <b>{record['wins']}–{record['losses']}–{record['draws']}</b>"
            f"{escape(streak_text)}\n"
            f"🏆 {escape(title_text)}\n"
            f"⚡ KO/TKO: {wins_by['ko_tko']} · Сабмишены: {wins_by['submission']}"
        ),
        escape(card["positioning"]),
    ]
    if career:
        blocks.append(escape(career[0]))
    if style:
        blocks.append(escape(style[0]))
    if fact:
        blocks.append(f"💡 <b>Интересный факт:</b> {escape(fact)}")
    blocks.append(f"#БоецДня #MMA #{escape(card['promotion'].upper())}")
    return "\n\n".join(blocks)


def _select_topic(card: dict, history: list[dict]) -> str | None:
    topic_ids = [angle.get("id") for angle in card.get("angles", []) if angle.get("id")]
    if not topic_ids:
        return None
    previous = [
        entry.get("content_topic")
        for entry in history
        if entry.get("fighter_id") == card["id"]
    ]
    for topic_id in topic_ids:
        if topic_id not in previous:
            return topic_id
    return topic_ids[len(previous) % len(topic_ids)]


def _fact_for_topic(card: dict, topic_id: str | None) -> str:
    facts = {fact["id"]: fact["text"] for fact in card.get("facts", [])}
    angle = next(
        (item for item in card.get("angles", []) if item.get("id") == topic_id),
        None,
    )
    if angle:
        for fact_id in angle.get("fact_ids", []):
            if fact_id in facts:
                return facts[fact_id]
    return next(iter(facts.values()), "")


def _streak_text(streak: dict) -> str:
    count = streak.get("count")
    if not isinstance(count, int) or count <= 0:
        return ""
    forms = (
        ("победа", "победы", "побед")
        if streak.get("type") == "win"
        else ("поражение", "поражения", "поражений")
    )
    label = _russian_count_form(count, forms)
    return f" · {count} {label}"


def _russian_count_form(count: int, forms: tuple[str, str, str]) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return forms[0]
    if count % 10 in {2, 3, 4} and count % 100 not in {12, 13, 14}:
        return forms[1]
    return forms[2]


def _title_or_rank(card: dict) -> str:
    current = card.get("titles", {}).get("current", [])
    if current:
        return current[0]["name_ru"]
    rank = card.get("stats", {}).get("promotion_rank")
    if isinstance(rank, int):
        return f"№{rank} рейтинга {card['promotion']}"
    former = card.get("titles", {}).get("former", [])
    if former:
        return former[0]["name_ru"]
    return f"{card['promotion']} · {card['weight_class']}"


def simulation_table(results: list[dict]) -> str:
    """Return a readable fixed-width report for a dry-run sequence."""
    header = "Day | Fighter | Gender | Image valid | Cycle | Repeated? | Fallback used?"
    rows = [header, "-" * len(header)]
    for item in results:
        rows.append(
            f"{item['day']:>3} | {item['card']['name_ru']} | {item['gender']} | "
            f"yes | {item['cycle']} | {'yes' if item['repeated'] else 'no'} | "
            f"{'yes' if item['fallback_used'] else 'no'}"
        )
    return "\n".join(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate Fighter of the Day rotation")
    parser.add_argument("--days", type=int, default=15)
    args = parser.parse_args()
    print(simulation_table(simulate_fighter_days(max(0, args.days))))


if __name__ == "__main__":
    main()
