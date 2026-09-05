"""Editorial scoring for relevant MMA stories."""


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


def calculate_score(news_item):
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

    return max(0, score)
