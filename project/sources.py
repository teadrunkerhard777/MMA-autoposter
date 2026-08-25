"""Declarative sources and optional source-specific article hooks."""

from datetime import datetime, timedelta, timezone


now = datetime.now(timezone.utc)

# The local source makes the template demonstrable without network access.
SOURCES = [
    {
        "name": "ExampleNews local demo",
        "type": "static",
        "enabled": True,
        "items": [
            {
                "title": "Python tooling project releases a faster test runner",
                "url": "https://example.invalid/python-test-runner",
                "published_at": now - timedelta(hours=2),
                "description": "The open-source release improves Python test feedback.",
                "article_text": (
                    "A community Python project released a faster test runner. "
                    "The software remains open source and works locally."
                ),
                "image_url": None,
            },
            {
                "title": "City council discusses a new parking policy",
                "url": "https://example.invalid/parking-policy",
                "published_at": now - timedelta(hours=1),
                "description": "A local government meeting covered parking rules.",
                "article_text": "The council discussed parking policy.",
                "image_url": None,
            },
        ],
    },
    {
        "name": "Example technology RSS",
        "type": "rss",
        "url": "https://example.com/feed.xml",
        "enabled": False,
    },
    {
        "name": "Example declarative HTML",
        "type": "html",
        "url": "https://example.com/news",
        "base_url": "https://example.com",
        "item_selector": "article.news-card",
        "title_selector": "h2 a[href]",
        "link_selector": "h2 a[href]",
        "date_selector": "time[datetime]",
        "description_selector": "p.summary",
        "enabled": False,
    },
]

# A project can register a reliable body extractor without changing core code.
SOURCE_EXTRACTORS = {}
SOURCE_STOP_MARKERS = {}

