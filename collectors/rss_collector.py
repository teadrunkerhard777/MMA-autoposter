from urllib.parse import urljoin

import feedparser
import requests
from bs4 import BeautifulSoup

from collectors.normalizer import normalize_item


def collect_rss(source):
    """Collect one RSS feed into the shared news_item format."""

    try:
        feed = _parse_feed(source)
    except (
        OSError,
        TypeError,
        ValueError,
        requests.RequestException,
    ) as error:
        print(f"RSS warning ({source['name']}): {type(error).__name__}")
        return []

    if feed.bozo:
        print(f"RSS warning ({source['name']}): {feed.bozo_exception}")

    entries = feed.entries
    limit = source.get("limit")
    if limit is not None:
        entries = entries[:max(0, int(limit))]

    items = []

    for entry in entries:
        raw_item = {
            "title": entry.get("title", ""),
            "url": entry.get("link", ""),
            "published_at": entry.get("published", ""),
            "description": entry.get("summary", ""),
        }

        if source.get("use_feed_content"):
            raw_item.update(_extract_feed_article(entry, source))

        items.append(normalize_item(raw_item, source["name"]))

    return items


def _parse_feed(source):
    timeout = source.get("feed_timeout")
    if timeout is None:
        return feedparser.parse(source["url"])

    response = requests.get(
        source["url"],
        headers=source.get("headers") or {},
        timeout=max(1, float(timeout)),
    )
    response.raise_for_status()
    return feedparser.parse(response.content)


def _extract_feed_article(entry, source):
    """Extract an opt-in full article and image from the same feed entry."""

    content = entry.get("content") or []
    html = content[0].get("value", "") if content else ""
    soup = BeautifulSoup(html, "html.parser")
    stop_markers = tuple(
        marker.casefold()
        for marker in source.get("feed_stop_markers", ())
    )
    paragraphs = []

    for node in soup.find_all("p"):
        paragraph = " ".join(node.get_text(" ", strip=True).split())

        if not paragraph:
            continue
        if stop_markers and paragraph.casefold().startswith(stop_markers):
            break

        paragraphs.append(paragraph)

    media = entry.get("media_content") or []
    image_url = next(
        (item.get("url", "").strip() for item in media if item.get("url")),
        "",
    )

    if not image_url:
        image = soup.find("img")
        image_url = image.get("src", "").strip() if image else ""

    return {
        "article_text": "\n\n".join(paragraphs),
        "image_url": urljoin(entry.get("link", ""), image_url) or None,
    }
