from copy import deepcopy
from datetime import datetime, timezone

from fighter_of_day import run_fighter_of_day
from publishing.telegram import TelegramSendResult
from storage.history import load_history, save_history


NOW = datetime(2026, 9, 6, 9, 0, tzinfo=timezone.utc)


def test_dry_run_does_not_call_telegram_or_change_history(tmp_path):
    history_path = tmp_path / "published.json"
    original = [{"title": "production", "url": "https://example.test/news"}]
    save_history(deepcopy(original), history_path)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("Telegram must not be called in DRY_RUN")

    selected = run_fighter_of_day(
        dry_run=True,
        history_path=history_path,
        send_photo=fail_if_called,
        selected_at=NOW,
    )

    assert selected["fighter_id"] == "islam_makhachev"
    assert selected["publication_status"] == "dry_run"
    assert load_history(history_path) == original


def test_confirmed_photo_publication_updates_shared_history(tmp_path):
    history_path = tmp_path / "published.json"
    save_history([], history_path)
    calls = []

    def succeed(photo, caption, filename, mime_type):
        calls.append((photo.read(3), caption, filename, mime_type))
        return TelegramSendResult(True, attempts=1)

    selected = run_fighter_of_day(
        dry_run=False,
        history_path=history_path,
        send_photo=succeed,
        selected_at=NOW,
    )

    history = load_history(history_path)
    assert calls[0][0] == b"\xff\xd8\xff"
    assert calls[0][2] == "photo.jpg"
    assert calls[0][3] == "image/jpeg"
    assert history == [selected["history_entry"]]
    assert selected["publication_status"] == "published"


def test_failed_photo_publication_does_not_update_history(tmp_path):
    history_path = tmp_path / "published.json"
    save_history([], history_path)

    selected = run_fighter_of_day(
        dry_run=False,
        history_path=history_path,
        send_photo=lambda *args, **kwargs: TelegramSendResult(False, "HTTP 400"),
        selected_at=NOW,
    )

    assert load_history(history_path) == []
    assert selected["publication_status"] == "failed"


def test_uncertain_photo_publication_does_not_update_history(tmp_path):
    history_path = tmp_path / "published.json"
    save_history([], history_path)

    selected = run_fighter_of_day(
        dry_run=False,
        history_path=history_path,
        send_photo=lambda *args, **kwargs: TelegramSendResult(
            False,
            "ReadTimeout",
            uncertain=True,
        ),
        selected_at=NOW,
    )

    assert load_history(history_path) == []
    assert selected["publication_status"] == "uncertain"
