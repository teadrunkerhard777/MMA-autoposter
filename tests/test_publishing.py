from datetime import datetime, timezone
from pathlib import Path

import pytest
import requests

from main import publish_selected_news
from publishing.telegram import (
    TelegramSendResult,
    TemporaryImage,
    send_telegram_photo,
)


def news(image_url=None):
    return {
        "title": "Python release",
        "url": "https://example.test/story",
        "source": "Example",
        "published_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "description": "Python software release",
        "article_text": "Python software release body",
        "image_url": image_url,
        "matched_topics": ["python"],
        "event_category": "python",
    }


def fail_if_called(*args, **kwargs):
    raise AssertionError("external function must not be called")


def test_dry_run_never_publishes_or_changes_history():
    history = []
    changed = publish_selected_news(
        [news("https://img.test/photo.jpg")],
        history,
        True,
        "single",
        send_post=fail_if_called,
        send_photo=fail_if_called,
        download_image=fail_if_called,
        add_history=fail_if_called,
    )

    assert changed is False
    assert history == []


def test_history_changes_once_after_confirmed_text_success():
    history = []
    additions = []

    def add(item, target, settings):
        additions.append(item["url"])
        target.append({"url": item["url"]})

    changed = publish_selected_news(
        [news()],
        history,
        False,
        "single",
        send_post=lambda text: TelegramSendResult(True),
        add_history=add,
    )

    assert changed is True
    assert additions == ["https://example.test/story"]
    assert len(history) == 1


def test_successful_remote_photo_does_not_call_text_fallback():
    history = []
    changed = publish_selected_news(
        [news("https://img.test/photo.jpg")],
        history,
        False,
        "single",
        send_post=fail_if_called,
        send_photo=lambda *args, **kwargs: TelegramSendResult(True),
    )

    assert changed is True
    assert len(history) == 1


def test_confirmed_remote_fetch_error_uses_temporary_file(tmp_path):
    image_path = tmp_path / "photo.jpg"
    image_path.write_bytes(b"image")
    calls = []

    def send_photo(photo, caption, **kwargs):
        calls.append(type(photo).__name__)

        if isinstance(photo, str):
            return TelegramSendResult(
                False,
                "failed to get HTTP URL content",
                remote_fetch_failed=True,
            )

        return TelegramSendResult(True)

    changed = publish_selected_news(
        [news("https://img.test/photo.jpg")],
        [],
        False,
        "single",
        send_post=fail_if_called,
        send_photo=send_photo,
        download_image=lambda url: TemporaryImage(
            image_path, "image/jpeg", 5
        ),
    )

    assert changed is True
    assert calls == ["str", "BufferedReader"]
    assert image_path.exists() is False


def test_read_timeout_result_does_not_retry_or_fallback():
    history = []
    changed = publish_selected_news(
        [news("https://img.test/photo.jpg")],
        history,
        False,
        "single",
        send_post=fail_if_called,
        send_photo=lambda *args, **kwargs: TelegramSendResult(
            False, "ReadTimeout", uncertain=True
        ),
        download_image=fail_if_called,
    )

    assert changed is False
    assert history == []


def test_sender_marks_real_read_timeout_uncertain_without_retry(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "test-chat")
    calls = []

    def timeout(*args, **kwargs):
        calls.append(1)
        raise requests.ReadTimeout

    monkeypatch.setattr("publishing.telegram.requests.post", timeout)
    result = send_telegram_photo(
        "https://img.test/photo.jpg",
        "caption",
    )

    assert result.uncertain is True
    assert len(calls) == 1

