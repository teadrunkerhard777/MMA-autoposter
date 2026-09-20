"""MMA-specific video searches and short editorial captions."""


VIDEO_SOURCES = ("Pexels", "Pixabay")
VIDEO_SEARCH_QUERIES = {
    "day": (
        "mma sparring",
        "kickboxing sparring",
        "muay thai pad work",
        "boxing heavy bag",
    ),
    "evening": (
        "mixed martial arts training",
        "boxing sparring",
        "muay thai training",
        "kickboxing training",
    ),
}
VIDEO_ORIENTATION = "portrait"
VIDEO_RESULTS_PER_RUN = 30
VIDEO_MAX_DURATION_SECONDS = 35
VIDEO_MAX_SIZE_BYTES = 49 * 1024 * 1024

VIDEO_RELEVANCE_TERMS = (
    "mma",
    "mixed martial arts",
    "boxing",
    "boxer",
    "kickboxing",
    "muay thai",
    "martial arts",
    "combat sport",
    "sparring",
)
VIDEO_REJECTION_TERMS = (
    "animation",
    "animated",
    "cartoon",
    "3d render",
    "3d animation",
    "ice cream",
    "food",
    "toy",
    "video game",
)
VIDEO_FEATURED_MEDIA_IDS = {
    "pexels:6296587",
    "pexels:6296447",
    "pexels:6296292",
    "pexels:4761806",
    "pexels:35030806",
    "pexels:35030839",
    "pixabay:54875",
    "pixabay:20112",
    "pixabay:167490",
}

# Stock libraries can publish different edits from one filming session under
# separate IDs. Treat those edits as one visual story for channel diversity.
VIDEO_DUPLICATE_GROUPS = {
    "pixabay:216568": "dark-studio-boxer-closeup",
    "pixabay:52101": "dark-studio-boxer-closeup",
}

VIDEO_NOTES = (
    "Скорость решает, но техника сохраняет силы.",
    "Работа на дистанции: один шаг часто важнее одного удара.",
    "Тренировка продолжается, пока движения не станут автоматическими.",
    "Контроль, тайминг и точность решают больше, чем суета.",
    "Баланс, реакция, точность — три детали одного эпизода.",
    "Короткий фрагмент большой работы, которая остаётся за кадром.",
    "В единоборствах спокойная голова почти всегда быстрее рук.",
    "Техника выглядит легко только после сотен повторений.",
    "Темп высокий, но каждое движение должно оставаться осознанным.",
    "Именно в тренировках вырабатывается чувство момента.",
)


def is_relevant_video(item):
    """Reject generic fitness footage returned for broad combat searches."""

    text = str(item.get("search_text") or "").casefold()
    return (
        any(term in text for term in VIDEO_RELEVANCE_TERMS)
        and not any(term in text for term in VIDEO_REJECTION_TERMS)
    )
