"""Publish one rights-cleared native video in a requested daily slot."""

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from config import DRY_RUN
from core.run_lock import AlreadyRunningError, single_instance_lock
from project.formatter import format_video_caption
from publishing.telegram import (
    MAX_VIDEO_SIZE_BYTES,
    TemporaryVideo,
    VideoDownloadError,
    download_video_temp,
    send_telegram_video,
)


VIDEO_QUEUE_FILE = Path("project/content/videos/index.json")
VIDEO_HISTORY_FILE = Path("storage/video_published.json")
VIDEO_ASSET_DIR = Path("project/content/videos/clips")
LOCAL_TIMEZONE = ZoneInfo("Asia/Yekaterinburg")


def load_json_list(path):
    try:
        with Path(path).open(encoding="utf-8") as file:
            value = json.load(file)
    except (OSError, json.JSONDecodeError):
        return []
    return value if isinstance(value, list) else []


def select_video(queue, history, slot):
    published_ids = {
        entry.get("id") for entry in history if isinstance(entry, dict)
    }
    for item in queue:
        if not isinstance(item, dict):
            continue
        if item.get("slot") != slot or item.get("id") in published_ids:
            continue
        if not item.get("rights_confirmed") or not item.get("license_note"):
            continue
        if not all(item.get(key) for key in ("id", "title", "source", "source_url")):
            continue
        if not (item.get("video_path") or item.get("video_url")):
            continue
        return item
    return None


def publish_video_slot(
    slot,
    dry_run=DRY_RUN,
    queue_path=VIDEO_QUEUE_FILE,
    history_path=VIDEO_HISTORY_FILE,
    download_video=download_video_temp,
    send_video=send_telegram_video,
):
    queue = load_json_list(queue_path)
    history = load_json_list(history_path)
    item = select_video(queue, history, slot)
    if item is None:
        print(f"Video queue: no eligible item for {slot}")
        return None

    temporary_video = None
    try:
        is_temporary = not bool(item.get("video_path"))
        temporary_video = (
            validate_local_video(item["video_path"])
            if item.get("video_path")
            else download_video(item["video_url"])
        )
        caption = format_video_caption(item)
        if dry_run:
            print("[DRY RUN] Telegram was not called")
            print(
                f"Video validated: {temporary_video.mime_type}, "
                f"{temporary_video.size_bytes} bytes"
            )
            print(caption)
            return item

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
            "id": item["id"],
            "slot": slot,
            "published_at": datetime.now(LOCAL_TIMEZONE).isoformat(),
            "source_url": item.get("source_url"),
        })
        with Path(history_path).open("w", encoding="utf-8") as file:
            json.dump(history, file, ensure_ascii=False, indent=2)
        return item
    except (VideoDownloadError, OSError) as error:
        print(f"Video rejected: {type(error).__name__}")
        return None
    finally:
        if (
            temporary_video
            and is_temporary
            and temporary_video.path.exists()
        ):
            temporary_video.path.unlink()


def validate_local_video(video_path, asset_dir=VIDEO_ASSET_DIR):
    """Validate a repository-owned MP4 without deleting it after use."""

    asset_root = Path(asset_dir).resolve()
    path = Path(video_path).resolve()
    try:
        path.relative_to(asset_root)
    except ValueError as error:
        raise VideoDownloadError("video path is outside the asset directory") from error
    if not path.is_file():
        raise VideoDownloadError("video file is missing")
    size_bytes = path.stat().st_size
    if size_bytes == 0 or size_bytes > MAX_VIDEO_SIZE_BYTES:
        raise VideoDownloadError("invalid video size")
    with path.open("rb") as video_file:
        header = video_file.read(32)
    if len(header) < 12 or header[4:8] != b"ftyp":
        raise VideoDownloadError("video bytes are not an MP4 container")
    return TemporaryVideo(path, "video/mp4", size_bytes)


def run():
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
