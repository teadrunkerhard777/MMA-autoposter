"""ExampleNews relevance rules and event categorization."""


TOPIC_KEYWORDS = {
    "python": ("python",),
    "software": ("software", "open source", "open-source"),
    "testing": ("test runner", "testing tool"),
    "security": ("security update", "vulnerability", "security patch"),
}


def is_relevant(news_item):
    """Accept neutral technology/software stories for the example channel."""

    text = (
        f"{news_item.get('title', '')} "
        f"{news_item.get('description', '')}"
    ).casefold()
    matched_topics = [
        topic
        for topic, keywords in TOPIC_KEYWORDS.items()
        if any(keyword in text for keyword in keywords)
    ]

    # The category is project data consumed by generic event deduplication.
    news_item["matched_topics"] = matched_topics
    news_item["event_category"] = matched_topics[0] if matched_topics else None
    news_item.setdefault("event_locations", [])
    return bool(matched_topics)

