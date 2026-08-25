"""Greedy editorial diversity selection for an already ranked news list."""

from processing.deduplicator import meaningful_tokens


DEFAULTS = {
    "text_limit": 1200,
    "min_shared_tokens": 4,
    "min_token_overlap": 0.35,
    "min_token_jaccard": 0.16,
    "stop_words": set(),
    "noise_prefixes": (),
}


def select_diverse(news_items, limit, settings=None):
    """Keep ranked order while excluding overly similar batch candidates."""

    items = list(news_items)
    limit = max(0, int(limit))

    if limit == 0:
        return []

    # Missing or disabled settings preserve the original top-N behavior.
    if not settings or settings.get("enabled") is False:
        return items[:limit]

    values = {**DEFAULTS, **settings}
    selected = []
    selected_tokens = []

    for item in items:
        candidate_tokens = _item_tokens(item, values)

        if any(
            _tokens_are_too_similar(candidate_tokens, existing, values)
            for existing in selected_tokens
        ):
            continue

        selected.append(item)
        selected_tokens.append(candidate_tokens)

        if len(selected) == limit:
            break

    return selected


def _item_tokens(news_item, settings):
    topics = news_item.get("matched_topics") or []

    if isinstance(topics, str):
        topics = [topics]

    body = " ".join(
        (
            str(news_item.get("description") or ""),
            str(news_item.get("article_text") or ""),
        )
    )
    text = " ".join(
        (
            str(news_item.get("title") or ""),
            str(body)[:settings["text_limit"]],
            str(news_item.get("event_category") or ""),
            " ".join(str(topic) for topic in topics),
        )
    )
    return meaningful_tokens(text, settings)


def _tokens_are_too_similar(first, second, settings):
    if not first or not second:
        return False

    shared = first & second

    if len(shared) < settings["min_shared_tokens"]:
        return False

    overlap = len(shared) / min(len(first), len(second))
    jaccard = len(shared) / len(first | second)
    return (
        overlap >= settings["min_token_overlap"]
        or jaccard >= settings["min_token_jaccard"]
    )
