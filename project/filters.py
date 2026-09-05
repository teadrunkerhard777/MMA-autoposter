"""MMA relevance, editorial signals, and event categorization."""

import re


PROMOTION_KEYWORDS = {
    "ufc": ("ufc", "юфс"),
    "aca": ("aca", "аса"),
    "pfl": ("pfl",),
    "one": ("one championship",),
    "bellator": ("bellator",),
    "rizin": ("rizin",),
}

PRIORITY_FIGHTERS = {
    "islam_makhachev": ("ислам махачев", "islam makhachev"),
    "petr_yan": ("пётр ян", "петр ян", "petr yan", "peter yan"),
    "khamzat_chimaev": ("хамзат чимаев", "khamzat chimaev"),
    "magomed_ankalaev": ("магомед анкалаев", "magomed ankalaev"),
    "alexander_volkanovski": (
        "александр волкановски",
        "alexander volkanovski",
    ),
    "ilia_topuria": ("илия топурия", "ilia topuria"),
    "alex_pereira": ("алекс перейра", "alex pereira"),
    "jon_jones": ("джон джонс", "jon jones"),
    "tom_aspinall": ("том аспиналл", "tom aspinall"),
    "shavkat_rakhmonov": ("шавкат рахмонов", "shavkat rakhmonov"),
    "conor_mcgregor": ("конор макгрегор", "conor mcgregor"),
}

MMA_KEYWORDS = (
    "mma",
    "мма",
    "mixed martial arts",
    "смешанн",
    "октагон",
)

FIGHT_CONTEXT_KEYWORDS = (
    "бой",
    "боев",
    "боец",
    "поедин",
    "соперник",
    "турнир",
    "титул",
    "дивизион",
    "нокаут",
    "сабмиш",
    "fight",
    "bout",
    "opponent",
    "event",
    "title",
    "knockout",
    "submission",
)

EVENT_CATEGORY_KEYWORDS = (
    ("fight_cancelled", ("отмен", "сорвался", "cancelled", "canceled")),
    ("injury", ("травм", "injury", "injured")),
    ("retirement", ("завершил карьер", "завершила карьер", "retire")),
    (
        "contract_move",
        ("контракт", "подписал", "покинул промоушен", "released", "signed"),
    ),
    (
        "fight_result",
        (
            "победил",
            "победила",
            "выиграл",
            "нокаутировал",
            "сабмишен",
            "defeats",
            "knockout",
            "submission",
        ),
    ),
    (
        "fight_announcement",
        (
            "объявил",
            "объявила",
            "объявил бой",
            "объявила бой",
            "проведёт",
            "проведет",
            "встретится",
            "соперник",
            "переговор",
            "booked",
            "will face",
            "faces",
        ),
    ),
    ("event_update", ("турнир", "кард", "event", "fight card")),
    (
        "statement",
        ("заявил", "заявила", "вызвал", "интервью", "says", "called out"),
    ),
)

EDITORIAL_SIGNAL_KEYWORDS = {
    "title_stakes": ("титул", "чемпион", "title", "champion"),
    "official": ("официально", "official", "confirmed", "подтвержд"),
    "knockout": ("нокаут", "knockout", "ko "),
    "conflict": ("конфликт", "скандал", "challenge", "вызвал"),
    "comeback": ("возвращ", "comeback", "return"),
}

RUMOR_KEYWORDS = (
    "слух",
    "по данным",
    "может получить",
    "возможный",
    "возможно",
    "вероятно",
    "переговор",
    "инсайдер",
    "rumor",
    "reportedly",
    "could face",
    "in talks",
)

TOKEN_KEYWORDS = {"ufc", "юфс", "aca", "аса", "pfl", "mma", "мма"}

EVERGREEN_CONTENT_TYPES = {
    "fact",
    "fighter",
    "history",
    "matchup",
    "women_mma",
}


def is_relevant(news_item):
    """Accept MMA stories and attach project-owned editorial metadata."""

    text = _item_text(news_item)
    promotions = _matches_by_name(text, PROMOTION_KEYWORDS)
    fighters = _matches_by_name(text, PRIORITY_FIGHTERS)
    queue = news_item.get("content_queue") or "news"
    requested_content_type = news_item.get("content_type")
    is_evergreen = (
        queue == "evergreen"
        and requested_content_type in EVERGREEN_CONTENT_TYPES
    )
    has_mma_term = _contains_any(text, MMA_KEYWORDS)
    has_fight_context = _contains_any(text, FIGHT_CONTEXT_KEYWORDS)
    relevant = bool(
        is_evergreen
        or promotions
        or has_mma_term
        or (fighters and has_fight_context)
    )

    if is_evergreen:
        category = f"evergreen_{requested_content_type}"
    else:
        category = _event_category(text) if relevant else None
    is_rumor = (
        relevant
        and not is_evergreen
        and _contains_any(text, RUMOR_KEYWORDS)
    )
    signals = (
        _matches_by_name(text, EDITORIAL_SIGNAL_KEYWORDS)
        if relevant
        else []
    )
    if is_rumor:
        signals = [signal for signal in signals if signal != "official"]

    topics = []
    if relevant:
        topics.extend(promotions)
        topics.append(category)
        if is_rumor:
            topics.append("rumor")

    news_item["matched_topics"] = _unique(topics)
    news_item["matched_promotions"] = promotions
    news_item["matched_fighters"] = fighters
    news_item["editorial_signals"] = signals
    news_item["content_queue"] = queue
    news_item["content_type"] = (
        requested_content_type
        if is_evergreen
        else ("rumor" if is_rumor else "news")
    )
    news_item["is_rumor"] = bool(is_rumor)
    news_item["event_category"] = category
    news_item.setdefault("event_locations", [])
    return relevant


def _item_text(news_item):
    return (
        f"{news_item.get('title', '')} "
        f"{news_item.get('description', '')}"
    ).casefold()


def _contains_any(text, keywords):
    return any(_contains_keyword(text, keyword) for keyword in keywords)


def _contains_keyword(text, keyword):
    if keyword in TOKEN_KEYWORDS:
        return re.search(rf"(?<!\w){re.escape(keyword)}(?!\w)", text) is not None
    return keyword in text


def _matches_by_name(text, groups):
    return [
        name
        for name, keywords in groups.items()
        if _contains_any(text, keywords)
    ]


def _event_category(text):
    for category, keywords in EVENT_CATEGORY_KEYWORDS:
        if _contains_any(text, keywords):
            return category
    return "fighter_news"


def _unique(values):
    return list(dict.fromkeys(value for value in values if value))
