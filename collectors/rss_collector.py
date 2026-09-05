import feedparser

from collectors.normalizer import normalize_item


def collect_rss(source):
    """Collect one RSS feed into the shared news_item format."""

    try:
        feed = feedparser.parse(source["url"])
    except (OSError, TypeError, ValueError) as error:
        print(f"RSS warning ({source['name']}): {type(error).__name__}")
        return []

    if feed.bozo:
        print(f"RSS warning ({source['name']}): {feed.bozo_exception}")

    entries = feed.entries
    limit = source.get("limit")
    if limit is not None:
        entries = entries[:max(0, int(limit))]

    return [
        normalize_item(
            {
                "title": entry.get("title", ""),
                "url": entry.get("link", ""),
                "published_at": entry.get("published", ""),
                "description": entry.get("summary", ""),
            },
            source["name"],
        )
        for entry in entries
    ]
