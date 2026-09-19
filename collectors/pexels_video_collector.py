"""Collect short, Telegram-compatible videos from the official Pexels API."""

import requests


PEXELS_VIDEO_SEARCH_URL = "https://api.pexels.com/v1/videos/search"
PEXELS_TIMEOUT = (10, 30)


class PexelsVideoError(Exception):
    """Expected Pexels configuration or response failure."""


def collect_pexels_videos(
    api_key, query, orientation, per_page, max_duration_seconds, max_size_bytes
):
    if not api_key:
        raise PexelsVideoError("PEXELS_API_KEY is missing")
    try:
        response = requests.get(
            PEXELS_VIDEO_SEARCH_URL,
            headers={"Authorization": api_key},
            params={
                "query": query,
                "orientation": orientation,
                "size": "medium",
                "per_page": per_page,
            },
            timeout=PEXELS_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as error:
        raise PexelsVideoError(type(error).__name__) from error

    videos = payload.get("videos") if isinstance(payload, dict) else None
    if not isinstance(videos, list):
        raise PexelsVideoError("Pexels returned an invalid video list")
    return [
        candidate
        for video in videos
        if (
            candidate := _normalize_video(
                video, max_duration_seconds, max_size_bytes
            )
        ) is not None
    ]


def _normalize_video(video, max_duration_seconds, max_size_bytes):
    if not isinstance(video, dict):
        return None
    duration = video.get("duration")
    if not isinstance(duration, int) or not 4 <= duration <= max_duration_seconds:
        return None
    video_file = _best_video_file(video.get("video_files"), max_size_bytes)
    page_url = video.get("url")
    if video_file is None or not isinstance(page_url, str):
        return None
    user = video.get("user") if isinstance(video.get("user"), dict) else {}
    media_id = video.get("id")
    return {
        "id": f"pexels:{media_id}",
        "media_id": f"pexels:{media_id}",
        "title": "Момент из мира единоборств",
        "url": page_url,
        "source_url": page_url,
        "source": "Pexels",
        "video_url": video_file["link"],
        "video_duration": duration,
        "video_size": video_file.get("file_size"),
        "creator_name": user.get("name"),
        "pexels_id": media_id,
    }


def _best_video_file(video_files, max_size_bytes):
    if not isinstance(video_files, list):
        return None
    suitable = []
    for item in video_files:
        if not isinstance(item, dict) or item.get("file_type") != "video/mp4":
            continue
        if not isinstance(item.get("link"), str):
            continue
        size = item.get("file_size")
        width, height = item.get("width") or 0, item.get("height") or 0
        if not isinstance(size, int) or not 0 < size <= max_size_bytes:
            continue
        if not width or not height or max(width, height) > 1920:
            continue
        suitable.append(item)
    if not suitable:
        return None
    return min(
        suitable,
        key=lambda item: (
            abs(max(item.get("width", 0), item.get("height", 0)) - 1080),
            item["file_size"],
        ),
    )
