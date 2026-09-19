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

VIDEO_NOTES = (
    "Скорость решает, но техника сохраняет силы.",
    "Работа на дистанции: один шаг часто важнее одного удара.",
    "Тренировка продолжается, пока движения не станут автоматическими.",
    "Хороший спарринг — это контроль, тайминг и уважение к партнёру.",
    "Баланс, реакция, точность — три детали одного эпизода.",
    "Короткий фрагмент большой работы, которая остаётся за кадром.",
    "В единоборствах спокойная голова почти всегда быстрее рук.",
    "Техника выглядит легко только после сотен повторений.",
    "Темп высокий, но каждое движение должно оставаться осознанным.",
    "Именно в таких раундах вырабатывается чувство момента.",
)
