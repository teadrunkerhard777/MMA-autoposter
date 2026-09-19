"""Collect and publish one licensed MMA video in a requested daily slot."""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from collectors.pexels_video_collector import (
    PexelsVideoError,
    collect_pexels_videos,
)
from collectors.pixabay_video_collector import (
    PixabayVideoError,
    collect_pixabay_videos,
)
from config import DRY_RUN
from core.environment import configure_ssl
from core.run_lock import AlreadyRunningError, single_instance_lock
from project.formatter import format_video_caption
from project.video_settings import (
    VIDEO_MAX_DURATION_SECONDS,
    VIDEO_MAX_SIZE_BYTES,
    VIDEO_NOTES,
    VIDEO_ORIENTATION,
    VIDEO_RESULTS_PER_RUN,
    VIDEO_SEARCH_QUERIES,
    VIDEO_SOURCES,
)
from publishing.telegram import (
    VideoDownloadError,
    download_video_temp,
    send_telegram_video,
)


VIDEO_HISTORY_FILE = Path("storage/video_published.json")
LOCAL_TIMEZONE = ZoneInfo("Asia/Yekaterinburg")


def load_json_list(path):
    try:
        with Path(path).open(encoding="utf-8") as file:
            value = json.load(file)
    except (OSError, json.JSONDecodeError):
        return []
    return value if isinstance(value, list) else []


def choose_search_query(slot, current_date=None):
    queries = VIDEO_SEARCH_QUERIES[slot]
    day = current_date or datetime.now(LOCAL_TIMEZONE).date()
    return queries[day.toordinal() % len(queries)]


def choose_source_order(slot, current_date=None):
    day = current_date or datetime.now(LOCAL_TIMEZONE).date()
    slot_offset = 0 if slot == "day" else 1
    preferred = (day.toordinal() + slot_offset) % len(VIDEO_SOURCES)
    return VIDEO_SOURCES[preferred:] + VIDEO_SOURCES[:preferred]


def collect_source_videos(source, query):
    if source == "Pexels":
        return collect_pexels_videos(
            os.getenv("PEXELS_API_KEY", "").strip(),
            query,
            VIDEO_ORIENTATION,
            VIDEO_RESULTS_PER_RUN,
            VIDEO_MAX_DURATION_SECONDS,
            VIDEO_MAX_SIZE_BYTES,
        )
    if source == "Pixabay":
        return collect_pixabay_videos(
            os.getenv("PIXABAY_API_KEY", "").strip(),
            query,
            VIDEO_RESULTS_PER_RUN,
            VIDEO_MAX_DURATION_SECONDS,
            VIDEO_MAX_SIZE_BYTES,
        )
    return []


def select_video(candidates, history):
    published_ids = {
        str(entry.get("media_id") or entry.get("id"))
        for entry in history
        if isinstance(entry, dict)
    }
    published_urls = {
        entry.get("source_url")
        for entry in history
        if isinstance(entry, dict) and entry.get("source_url")
    }
    return next(
        (
            item
            for item in candidates
            if str(item.get("media_id")) not in published_ids
            and item.get("source_url") not in published_urls
        ),
        None,
    )


def prepare_caption(item):
    media_id = str(item.get("media_id") or "video")
    prepared = dict(item)
    prepared["note"] = VIDEO_NOTES[
        sum(media_id.encode("utf-8")) % len(VIDEO_NOTES)
    ]
    return format_video_caption(prepared)


def publish_video_slot(
    slot,
    dry_run=DRY_RUN,
    history_path=VIDEO_HISTORY_FILE,
    collect_source=collect_source_videos,
    download_video=download_video_temp,
    send_video=send_telegram_video,
    current_date=None,
):
    history = load_json_list(history_path)
    query = choose_search_query(slot, current_date)
    print(f"Video query ({slot}): {query}")
    selected = None
    for source in choose_source_order(slot, current_date):
        try:
            candidates = collect_source(source, query)
        except (PexelsVideoError, PixabayVideoError) as error:
            print(f"Video source warning ({source}): {error}")
            continue
        print(f"Suitable videos ({source}): {len(candidates)}")
        selected = select_video(candidates, history)
        if selected is not None:
            break
    if selected is None:
        print(f"Video search: no unpublished item for {slot}")
        return None

    temporary_video = None
    try:
        temporary_video = download_video(selected["video_url"])
        caption = prepare_caption(selected)
        if dry_run:
            print("[DRY RUN] Telegram was not called")
            print(
                f"Video validated: {temporary_video.mime_type}, "
                f"{temporary_video.size_bytes} bytes"
            )
            print(caption)
            return selected
        with temporary_video.path.open("rb") as video_file:
            result = send_video(
                video_file,
                caption,
                filename=temporary_video.path.name,
                mime_type=temporary_video.mime_type,
            )
        if not result:
            return None
        history.append({
            "id": selected["media_id"],
            "media_id": selected["media_id"],
            "slot": slot,
            "published_at": datetime.now(LOCAL_TIMEZONE).isoformat(),
            "source_url": selected.get("source_url"),
            "source": selected.get("source"),
        })
        Path(history_path).write_text(
            json.dumps(history, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return selected
    except (VideoDownloadError, OSError) as error:
        print(f"Video rejected: {type(error).__name__}")
        return None
    finally:
        if temporary_video and temporary_video.path.exists():
            temporary_video.path.unlink()


def run():
    configure_ssl()
    parser = argparse.ArgumentParser()
    parser.add_argument("--slot", choices=("day", "evening"), required=True)
    args = parser.parse_args()
    return publish_video_slot(args.slot)


if __name__ == "__main__":
    try:
        with single_instance_lock():
            run()
    except AlreadyRunningError:
        print("Autoposter is already running; this run was stopped.")
