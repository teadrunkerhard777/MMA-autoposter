"""ExampleNews scoring rules."""


TOPIC_SCORES = {
    "python": 3,
    "security": 3,
    "software": 2,
    "testing": 1,
}


def calculate_score(news_item):
    """Score a relevant item using the project's matched topics."""

    return sum(
        TOPIC_SCORES.get(topic, 0)
        for topic in news_item.get("matched_topics", [])
    )

