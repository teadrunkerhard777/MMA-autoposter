"""Publish one Fighter of the Day entry using the project content database."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from config import DRY_RUN
from core.run_lock import AlreadyRunningError, single_instance_lock
from project.fighter_cards import load_fighter_cards
from project.fighter_of_day import select_next_fighter
from publishing.telegram import send_telegram_photo
from storage.history import HISTORY_FILE, load_history, save_history


def run_fighter_of_day(
    dry_run=DRY_RUN,
    history_path=HISTORY_FILE,
    send_photo=send_telegram_photo,
    selected_at=None,
):
    """Select and optionally publish one fighter without ambiguous retries."""
    history = load_history(history_path)
    moment = selected_at or datetime.now(timezone.utc)
    selected = select_next_fighter(load_fighter_cards(), history, moment)
    if selected is None:
        print("Fighter of the Day: no eligible fighters")
        return None

    print(
        "Fighter of the Day: "
        f"{selected['card']['name_ru']} · {selected['gender']} · "
        f"cycle {selected['cycle']} · topic {selected['content_topic']}"
    )
    print(f"Image: {selected['image_path']} · valid")

    if dry_run:
        print("[DRY RUN] Telegram was not called")
        print(selected["post_html"])
        selected["publication_status"] = "dry_run"
        return selected

    image_path = Path(selected["image_path"])
    try:
        with image_path.open("rb") as image_file:
            result = send_photo(
                image_file,
                selected["post_html"],
                filename=image_path.name,
                mime_type="image/jpeg",
            )
    except OSError as error:
        print(f"Fighter image error: {type(error).__name__}")
        selected["publication_status"] = "failed"
        return selected

    if result:
        history.append(selected["history_entry"])
        save_history(history, history_path)
        selected["publication_status"] = "published"
        print("Fighter of the Day: publication confirmed and history updated")
    elif getattr(result, "uncertain", False):
        selected["publication_status"] = "uncertain"
        print("Fighter of the Day: delivery uncertain; history not updated")
    else:
        selected["publication_status"] = "failed"
        print("Fighter of the Day: publication failed; history not updated")
    return selected


if __name__ == "__main__":
    try:
        with single_instance_lock():
            outcome = run_fighter_of_day()
            if outcome is None or outcome.get("publication_status") in {
                "failed",
                "uncertain",
            }:
                raise SystemExit(1)
    except AlreadyRunningError:
        print("Autoposter is already running; this run was stopped.")
