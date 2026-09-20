from datetime import date, datetime
from zoneinfo import ZoneInfo

from publishing.telegram import TelegramSendResult, TemporaryVideo
from video_posts import (
    choose_search_query,
    choose_source_order,
    prepare_caption,
    publish_video_slot,
    resolve_slot,
    select_video,
)


def video(**changes):
    value = {
        "id": "pexels:42",
        "media_id": "pexels:42",
        "title": "Момент из мира единоборств",
        "source": "Pexels",
        "source_url": "https://www.pexels.com/video/42/",
        "video_url": "https://video.test/42.mp4",
        "search_text": "mma sparring",
    }
    value.update(changes)
    return value


def test_slots_rotate_queries_and_preferred_sources():
    today = date(2026, 9, 19)
    assert choose_search_query("day", today) != choose_search_query(
        "evening", today
    )
    assert choose_source_order("day", today)[0] != choose_source_order(
        "evening", today
    )[0]


def test_auto_slot_uses_yekaterinburg_local_time():
    timezone = ZoneInfo("Asia/Yekaterinburg")

    assert resolve_slot("auto", datetime(2026, 9, 19, 13, tzinfo=timezone)) == "day"
    assert resolve_slot("auto", datetime(2026, 9, 19, 20, tzinfo=timezone)) == "evening"
    assert resolve_slot("day") == "day"


def test_selection_skips_published_id_and_source_url():
    old = video()
    fresh = video(
        id="pixabay:77",
        media_id="pixabay:77",
        source_url="https://pixabay.com/videos/id-77/",
    )
    assert select_video([old, fresh], [{"media_id": old["media_id"]}]) == fresh
    assert select_video([old], [{"source_url": old["source_url"]}]) is None


def test_selection_rejects_generic_fitness_and_prefers_curated_video():
    fitness = video(
        id="pixabay:293085",
        media_id="pixabay:293085",
        search_text="woman fitness exercise workout",
    )
    ordinary = video(id="pexels:99", media_id="pexels:99")
    featured = video(id="pexels:6296587", media_id="pexels:6296587")

    assert select_video([fitness], []) is None
    assert select_video([ordinary, featured], []) == featured

    animated_food = video(
        id="pixabay:61116",
        media_id="pixabay:61116",
        search_text="ice cream boxing fight fighting 3d animation",
    )
    assert select_video([animated_food], []) is None


def test_selection_rejects_different_id_from_same_visual_series():
    previous_edit = {"media_id": "pixabay:216568"}
    same_boxer_new_edit = video(
        id="pixabay:52101",
        media_id="pixabay:52101",
        search_text="boxer athlete gloves box fighting",
    )

    assert select_video([same_boxer_new_edit], [previous_edit]) is None


def test_caption_is_short_note_with_clickable_source():
    caption = prepare_caption(video())
    assert "Момент из мира единоборств" in caption
    assert '<a href="https://www.pexels.com/video/42/">Pexels</a>' in caption
    assert "#MMAVideo" in caption


def test_dry_run_uses_fallback_and_does_not_send_or_write_history(tmp_path):
    history_path = tmp_path / "history.json"
    history_path.write_text("[]", encoding="utf-8")
    video_path = tmp_path / "video.mp4"
    video_path.write_bytes(b"video")

    def collect(source, query):
        return [] if source == "Pexels" else [video(source="Pixabay")]

    selected = publish_video_slot(
        "day",
        dry_run=True,
        history_path=history_path,
        collect_source=collect,
        download_video=lambda url: TemporaryVideo(video_path, "video/mp4", 5),
        send_video=lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("Telegram must not be called")
        ),
        current_date=date(2026, 9, 19),
    )

    assert selected["media_id"] == "pexels:42"
    assert history_path.read_text(encoding="utf-8") == "[]"
    assert not video_path.exists()


def test_confirmed_send_appends_dynamic_media_history(tmp_path):
    history_path = tmp_path / "history.json"
    history_path.write_text("[]", encoding="utf-8")
    video_path = tmp_path / "video.mp4"
    video_path.write_bytes(b"video")

    selected = publish_video_slot(
        "evening",
        dry_run=False,
        history_path=history_path,
        collect_source=lambda source, query: [video()],
        download_video=lambda url: TemporaryVideo(video_path, "video/mp4", 5),
        send_video=lambda *args, **kwargs: TelegramSendResult(True),
        current_date=date(2026, 9, 19),
    )

    assert selected["media_id"] == "pexels:42"
    assert '"media_id": "pexels:42"' in history_path.read_text(
        encoding="utf-8"
    )
    assert not video_path.exists()
