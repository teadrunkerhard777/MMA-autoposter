"""Settings a new autoposter owner is expected to edit first."""

NEWS_LOOKBACK_DAYS = 3
MAX_NEWS_PER_RUN = 1
MIN_PUBLICATION_SCORE = 5
EVERGREEN_SLOTS_PER_RUN = 2
POST_MODE = "single"

# Event dedup is generic; projects tune only its data and thresholds.
EVENT_DEDUP_SETTINGS = {
    "text_limit": 1600,
    "time_window_hours": 36,
    "min_shared_tokens": 5,
    "min_token_overlap": 0.45,
    "min_token_jaccard": 0.20,
    "dense_match_tokens": 7,
    "event_time_window_hours": 24,
    "event_date_window_days": 0,
    "min_shared_participants": 2,
    "stop_words": {
        "about", "after", "also", "from", "into", "more", "that",
        "their", "this", "with", "will", "your", "будет", "были",
        "было", "для", "его", "как", "который", "матч", "после",
        "при", "свой", "этот",
    },
    "noise_prefixes": (
        "announce", "article", "company", "report", "source", "update",
        "анонс", "источник", "материал", "сообщ",
    ),
}

# Diversity is a softer batch-level check applied after event deduplication.
DIVERSITY_SETTINGS = {
    "enabled": True,
    "text_limit": 1200,
    "core_min_shared_tokens": 4,
    "core_min_token_overlap": 0.30,
    "core_min_token_jaccard": 0.14,
    "core_dense_match_tokens": 5,
    "min_shared_tokens": 4,
    "min_token_overlap": 0.35,
    "min_token_jaccard": 0.16,
    "stop_words": {
        "about", "after", "also", "from", "into", "more", "that",
        "their", "this", "with", "will", "your", "будет", "были",
        "было", "для", "его", "как", "который", "матч", "после",
        "при", "свой", "этот",
    },
    "noise_prefixes": (
        "announce", "article", "company", "report", "source", "update",
        "анонс", "источник", "материал", "сообщ",
    ),
}
