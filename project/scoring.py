"""Editorial scoring for relevant MMA stories."""

from project.scheduling import event_window


CATEGORY_SCORES = {
    "fight_cancelled": 9,
    "injury": 8,
    "fight_result": 7,
    "fight_announcement": 7,
    "retirement": 7,
    "contract_move": 6,
    "event_update": 5,
    "statement": 4,
    "fighter_news": 3,
    "evergreen_fighter": 6,
    "evergreen_women_mma": 6,
    "evergreen_matchup": 6,
    "evergreen_fact": 5,
    "evergreen_history": 5,
}

PROMOTION_SCORES = {
    "ufc": 3,
    "aca": 2,
    "pfl": 2,
    "one": 2,
    "bellator": 2,
    "rizin": 2,
}

SIGNAL_SCORES = {
    "title_stakes": 3,
    "official": 2,
    "knockout": 2,
    "conflict": 1,
    "comeback": 2,
}

PRIORITY_FIGHTER_SCORE = 3
MAX_PRIORITY_FIGHTER_BONUS = 6
RUMOR_PENALTY = 2

EVENT_WINDOW_SCORES = {
    "next_48_hours": 8,
    "next_7_days": 4,
    "later": 0,
    "past": 0,
}

BREAKING_CATEGORY_SCORES = {
    "fight_cancelled": 9,
    "injury": 8,
}


def calculate_score(news_item, now=None):
    """Rank relevant stories without bypassing the relevance gate."""

    score = CATEGORY_SCORES.get(news_item.get("event_category"), 0)
    score += sum(
        PROMOTION_SCORES.get(promotion, 0)
        for promotion in news_item.get("matched_promotions", [])
    )
    score += sum(
        SIGNAL_SCORES.get(signal, 0)
        for signal in news_item.get("editorial_signals", [])
    )
    fighter_bonus = len(news_item.get("matched_fighters", [])) * (
        PRIORITY_FIGHTER_SCORE
    )
    score += min(fighter_bonus, MAX_PRIORITY_FIGHTER_BONUS)

    if news_item.get("is_rumor"):
        score -= RUMOR_PENALTY

    window = event_window(news_item.get("event_at"), now)
    news_item["event_window"] = window
    score += EVENT_WINDOW_SCORES.get(window, 0)

    category = news_item.get("event_category")
    score += BREAKING_CATEGORY_SCORES.get(category, 0)
    if category in BREAKING_CATEGORY_SCORES:
        news_item["editorial_priority"] = "breaking"
    elif window == "next_48_hours":
        news_item["editorial_priority"] = "next_48_hours"
    elif window == "next_7_days":
        news_item["editorial_priority"] = "next_7_days"
    elif news_item.get("content_queue") == "evergreen":
        news_item["editorial_priority"] = "scheduled"
    else:
        news_item["editorial_priority"] = "standard"

    return max(0, score)
