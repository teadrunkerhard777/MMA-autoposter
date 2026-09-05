"""Editorial batch selection across reactive and scheduled content."""

from processing.diversity import select_diverse


PRIORITY_NEWS = {"breaking", "next_48_hours"}
EDITORIAL_PRIORITY_RANK = {
    "breaking": 5,
    "next_48_hours": 4,
    "next_7_days": 3,
    "major_story": 2,
    "standard": 1,
    "scheduled": 0,
}


def sort_by_editorial_priority(news_items):
    """Keep editorial tiers strict, then use score inside each tier."""

    return sorted(
        news_items,
        key=lambda item: (
            EDITORIAL_PRIORITY_RANK.get(
                item.get("editorial_priority"),
                EDITORIAL_PRIORITY_RANK["standard"],
            ),
            item.get("score", 0),
        ),
        reverse=True,
    )


def select_editorial_mix(
    news_items,
    limit,
    diversity_settings,
    evergreen_slots,
):
    """Reserve evergreen slots unless urgent news needs the whole batch."""

    items = list(news_items)
    limit = max(0, int(limit))
    evergreen_slots = max(0, int(evergreen_slots))
    if limit == 0:
        return []

    reactive = [
        item for item in items
        if item.get("content_queue") != "evergreen"
    ]
    evergreen = [
        item for item in items
        if item.get("content_queue") == "evergreen"
    ]

    reserved = min(evergreen_slots, len(evergreen), limit)
    priority_count = sum(
        item.get("editorial_priority") in PRIORITY_NEWS
        for item in reactive
    )
    reserved = min(reserved, max(0, limit - priority_count))

    selected_evergreen = select_diverse(
        evergreen,
        reserved,
        diversity_settings,
    )
    selected_reactive = select_diverse(
        reactive,
        limit - len(selected_evergreen),
        diversity_settings,
    )

    return selected_reactive + selected_evergreen
