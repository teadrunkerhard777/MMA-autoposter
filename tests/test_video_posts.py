import json

import pytest

from publishing.telegram import (
    TelegramSendResult,
    TemporaryVideo,
    VideoDownloadError,
    download_video_temp,
)
from video_posts import publish_video_slot, select_video


def item(**changes):
    value = {
        "id": "clip-1",
        "slot": "day",
        "title": "Moment",
        "note": "What happened.",
        "video_url": "https://cdn.test/clip.mp4",
        "source": "Owner",
        "source_url": "https://owner.test/post",
        "rights_confirmed": True,
        "license_note": "Used with permission",
    }
    value.update(changes)
    return value


def test_selection_requires_matching_slot_rights_and_unused_id():
    assert select_video([item()], [], "day")["id"] == "clip-1"
    assert select_video([item()], [], "evening") is None
    assert select_video([item(rights_confirmed=False)], [], "day") is None
    assert select_video([item()], [{"id": "clip-1"}], "day") is None


def test_dry_run_validates_and_removes_video_without_send_or_history(tmp_path):
    queue_path = tmp_path / "queue.json"
    queue_path.write_text(json.dumps([item()]), encoding="utf-8")
    history_path = tmp_path / "history.json"
    history_path.write_text("[]", encoding="utf-8")
    video_path = tmp_path / "clip.mp4"
    video_path.write_bytes(b"video")

    selected = publish_video_slot(
        "day",
        dry_run=True,
        queue_path=queue_path,
        history_path=history_path,
        download_video=lambda url: TemporaryVideo(video_path, "video/mp4", 5),
        send_video=lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("Telegram must not be called")
        ),
    )

    assert selected["id"] == "clip-1"
    assert history_path.read_text(encoding="utf-8") == "[]"
    assert not video_path.exists()


def test_confirmed_send_updates_history(tmp_path):
    queue_path = tmp_path / "queue.json"
    queue_path.write_text(json.dumps([item()]), encoding="utf-8")
    history_path = tmp_path / "history.json"
    history_path.write_text("[]", encoding="utf-8")
    video_path = tmp_path / "clip.mp4"
    video_path.write_bytes(b"video")

    selected = publish_video_slot(
        "day",
        dry_run=False,
        queue_path=queue_path,
        history_path=history_path,
        download_video=lambda url: TemporaryVideo(video_path, "video/mp4", 5),
        send_video=lambda *args, **kwargs: TelegramSendResult(True),
    )

    assert selected["id"] == "clip-1"
    assert '"id": "clip-1"' in history_path.read_text(encoding="utf-8")
    assert not video_path.exists()


class VideoResponse:
    def __init__(self, body, content_type="video/mp4"):
        self.body = body
        self.headers = {
            "Content-Type": content_type,
            "Content-Length": str(len(body)),
        }

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size):
        yield self.body

    def close(self):
        return None


def test_video_download_accepts_mp4_and_removes_temp_after_use(monkeypatch):
    body = b"\x00\x00\x00\x18ftypisom" + b"0" * 20
    monkeypatch.setattr(
        "publishing.telegram.requests.get",
        lambda *args, **kwargs: VideoResponse(body),
    )

    video = download_video_temp("https://cdn.test/clip.mp4")
    try:
        assert video.mime_type == "video/mp4"
        assert video.path.read_bytes() == body
    finally:
        video.path.unlink()


def test_video_download_rejects_non_mp4(monkeypatch):
    monkeypatch.setattr(
        "publishing.telegram.requests.get",
        lambda *args, **kwargs: VideoResponse(b"not-video", "text/html"),
    )

    with pytest.raises(VideoDownloadError):
        download_video_temp("https://cdn.test/clip.mp4")
