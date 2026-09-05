"""Project-owned visual roles for MMA posts."""


VISUAL_TYPES = {
    "NEWS",
    "FIGHTER",
    "VS",
    "QUOTE",
    "EVENT",
    "FACT",
    "RESULT",
}

CATEGORY_VISUAL_TYPES = {
    "fight_result": "RESULT",
    "fight_announcement": "EVENT",
    "event_update": "EVENT",
    "statement": "QUOTE",
    "evergreen_fighter": "FIGHTER",
    "evergreen_women_mma": "FIGHTER",
    "evergreen_matchup": "VS",
    "evergreen_fact": "FACT",
    "evergreen_history": "FACT",
}


def visual_type_for(news_item):
    """Return the intended visual treatment without generating an image."""

    return CATEGORY_VISUAL_TYPES.get(
        news_item.get("event_category"),
        "NEWS",
    )
