"""Collect short, Telegram-compatible videos from the official Pixabay API."""

import requests


PIXABAY_VIDEO_SEARCH_URL = "https://pixabay.com/api/videos/"
PIXABAY_TIMEOUT = (10, 30)


class PixabayVideoError(Exception):
    """Expected Pixabay configuration or response failure."""


def collect_pixabay_videos(
    api_key, query, per_page, max_duration_seconds, max_size_bytes
):
    if not api_key:
        raise PixabayVideoError("PIXABAY_API_KEY is missing")
    try:
        response = requests.get(
            PIXABAY_VIDEO_SEARCH_URL,
            params={
                "key": api_key,
                "q": query,
                "category": "sports",
                "safesearch": "true",
                "order": "popular",
                "per_page": per_page,
            },
            timeout=PIXABAY_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as error:
        raise PixabayVideoError(type(error).__name__) from error

    videos = payload.get("hits") if isinstance(payload, dict) else None
    if not isinstance(videos, list):
        raise PixabayVideoError("Pixabay returned an invalid video list")
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
    video_file = _best_video_file(video.get("videos"), max_size_bytes)
    page_url = video.get("pageURL")
    if video_file is None or not isinstance(page_url, str):
        return None
    media_id = video.get("id")
    return {
        "id": f"pixabay:{media_id}",
        "media_id": f"pixabay:{media_id}",
        "title": "Момент из мира единоборств",
        "url": page_url,
        "source_url": page_url,
        "source": "Pixabay",
        "video_url": video_file["url"],
        "video_duration": duration,
        "video_size": video_file.get("size"),
        "search_text": " ".join(
            str(value)
            for value in (video.get("tags"), video.get("type"))
            if value
        ),
        "pixabay_id": media_id,
    }


def _best_video_file(video_files, max_size_bytes):
    if not isinstance(video_files, dict):
        return None
    suitable = []
    for item in video_files.values():
        if not isinstance(item, dict) or not isinstance(item.get("url"), str):
            continue
        size = item.get("size")
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
            item["size"],
        ),
    )
