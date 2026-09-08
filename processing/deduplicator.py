import re
from datetime import date, datetime, timedelta, timezone
from difflib import SequenceMatcher
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


DEFAULTS = {
    "text_limit": 1600,
    "time_window_hours": 36,
    "min_shared_tokens": 5,
    "min_token_overlap": 0.45,
    "min_token_jaccard": 0.20,
    "dense_match_tokens": 7,
    "event_time_window_hours": 24,
    "event_date_window_days": 0,
    "min_shared_participants": 2,
    "stop_words": set(),
    "noise_prefixes": (),
}

TRACKING_QUERY_KEYS = {"fbclid", "gclid", "ref", "source"}


def normalize_title(title):
    normalized = re.sub(r"[^\w\s]", " ", (title or "").casefold())
    return " ".join(normalized.split())


def title_similarity(first, second):
    return SequenceMatcher(
        None,
        normalize_title(first),
        normalize_title(second),
    ).ratio()


def titles_are_similar(first, second, threshold=0.75):
    return title_similarity(first, second) >= threshold


def normalize_url(url):
    """Remove fragments and known tracking parameters from an article URL."""

    try:
        parts = urlsplit(url or "")
    except (TypeError, ValueError):
        return str(url or "").strip()

    query = urlencode(sorted(
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.casefold().startswith("utm_")
        and key.casefold() not in TRACKING_QUERY_KEYS
    ))
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((
        parts.scheme.casefold(),
        parts.netloc.casefold(),
        path,
        query,
        "",
    ))


def meaningful_tokens(text, settings=None):
    """Return generic normalized tokens shared by dedup and selection."""

    return _meaningful_tokens(text, _settings(settings))


def remove_duplicates(news_items, settings=None, debug=False):
    """Remove URL, title, and conservative cross-source event duplicates."""

    unique = []
    seen_urls = set()

    for item in news_items:
        url = normalize_url(item.get("url", ""))

        if url and url in seen_urls:
            continue

        duplicate_index = None
        event_details = None

        for index, existing in enumerate(unique):
            if (
                titles_are_similar(item.get("title"), existing.get("title"))
                and not _participants_conflict(item, existing, settings)
            ):
                duplicate_index = index
                break

            details = compare_event_fingerprints(item, existing, settings)

            if details["is_duplicate"]:
                duplicate_index = index
                event_details = details
                break

        if duplicate_index is None:
            if url:
                seen_urls.add(url)
            _attach_confirmed_sources(item)
            unique.append(item)
            continue

        if url:
            seen_urls.add(url)

        existing = unique[duplicate_index]
        confirmed_sources = _confirmed_sources(existing, item)

        # Title duplicates preserve stable first occurrence, but still record
        # an independent editorial confirmation.
        if event_details is None:
            _attach_confirmed_sources(existing, confirmed_sources)
            continue

        preferred = _choose_preferred(existing, item)

        if debug:
            print(
                "[EVENT DEDUP] "
                f"{existing.get('source')} / {item.get('source')}: "
                f"{', '.join(event_details['shared_tokens'])}"
            )

        if preferred is item:
            _attach_confirmed_sources(item, confirmed_sources)
            unique[duplicate_index] = item
        else:
            _attach_confirmed_sources(existing, confirmed_sources)

    return unique


def build_event_fingerprint(news_item, settings=None):
    """Build a project-neutral fingerprint from category, text, and hints."""

    values = _settings(settings)
    body = news_item.get("article_text") or news_item.get("description", "")
    text = f"{news_item.get('title', '')} {body[:values['text_limit']]}"
    category = news_item.get("event_category")
    event_at = _parse_event_datetime(news_item.get("event_at"))
    event_date = _parse_event_date(news_item.get("event_date"))

    return {
        "categories": [category] if category else [],
        "tokens": sorted(_meaningful_tokens(text, values)),
        "participants": sorted(set(news_item.get("event_participants", []))),
        "event_at": event_at.isoformat() if event_at else None,
        "event_date": event_date.isoformat() if event_date else None,
        # Geography is optional project data, never a global requirement.
        "locations": sorted(set(news_item.get("event_locations", []))),
    }


def compare_event_fingerprints(first, second, settings=None):
    """Compare two different-source items using configurable generic facts."""

    values = _settings(settings)
    result = {
        "is_duplicate": False,
        "shared_tokens": [],
        "shared_categories": [],
        "shared_locations": [],
        "shared_participants": [],
        "token_overlap": 0.0,
        "token_jaccard": 0.0,
        "time_delta_hours": None,
        "event_time_delta_hours": None,
        "event_date_delta_days": None,
    }

    if first.get("source") and first.get("source") == second.get("source"):
        return result

    first_fp = _read_or_build(first, values)
    second_fp = _read_or_build(second, values)
    first_event_at = _parse_event_datetime(first_fp.get("event_at"))
    second_event_at = _parse_event_datetime(second_fp.get("event_at"))
    first_event_date = _parse_event_date(first_fp.get("event_date"))
    second_event_date = _parse_event_date(second_fp.get("event_date"))

    if first_event_at is not None and second_event_at is not None:
        event_delta = abs(first_event_at - second_event_at)
        result["event_time_delta_hours"] = (
            event_delta.total_seconds() / 3600
        )
        if event_delta > timedelta(hours=values["event_time_window_hours"]):
            return result
    elif first_event_date is not None and second_event_date is not None:
        event_date_delta = abs((first_event_date - second_event_date).days)
        result["event_date_delta_days"] = event_date_delta
        if event_date_delta > values["event_date_window_days"]:
            return result
    else:
        first_date = _parse_datetime(first.get("published_at"))
        second_date = _parse_datetime(second.get("published_at"))

        if first_date is None or second_date is None:
            return result

        delta = abs(first_date - second_date)
        result["time_delta_hours"] = delta.total_seconds() / 3600

        if delta > timedelta(hours=values["time_window_hours"]):
            return result

    shared_categories = (
        set(first_fp.get("categories", []))
        & set(second_fp.get("categories", []))
    )

    if not shared_categories:
        return result

    first_tokens = set(first_fp.get("tokens", []))
    second_tokens = set(second_fp.get("tokens", []))
    first_participants = set(first_fp.get("participants", []))
    second_participants = set(second_fp.get("participants", []))
    shared_participants = first_participants & second_participants

    if first_participants and second_participants:
        if len(shared_participants) < values["min_shared_participants"]:
            return result
        return {
            **result,
            "is_duplicate": True,
            "shared_categories": sorted(shared_categories),
            "shared_participants": sorted(shared_participants),
        }

    if not first_tokens or not second_tokens:
        return result

    shared_tokens = first_tokens & second_tokens
    token_overlap = len(shared_tokens) / min(len(first_tokens), len(second_tokens))
    token_jaccard = len(shared_tokens) / len(first_tokens | second_tokens)
    shared_locations = (
        set(first_fp.get("locations", []))
        & set(second_fp.get("locations", []))
    )
    enough_facts = (
        len(shared_tokens) >= values["min_shared_tokens"]
        and token_overlap >= values["min_token_overlap"]
    )
    location_or_dense = bool(shared_locations) or (
        len(shared_tokens) >= values["dense_match_tokens"]
        and token_jaccard >= values["min_token_jaccard"]
    )

    return {
        **result,
        "is_duplicate": enough_facts and location_or_dense,
        "shared_tokens": sorted(shared_tokens),
        "shared_categories": sorted(shared_categories),
        "shared_locations": sorted(shared_locations),
        "shared_participants": sorted(shared_participants),
        "token_overlap": token_overlap,
        "token_jaccard": token_jaccard,
    }


def _settings(settings):
    return {**DEFAULTS, **(settings or {})}


def _read_or_build(item, settings):
    fingerprint = item.get("event_fingerprint")
    return fingerprint if isinstance(fingerprint, dict) else build_event_fingerprint(item, settings)


def _participants_conflict(first, second, settings=None):
    values = _settings(settings)
    first_participants = set(
        _read_or_build(first, values).get("participants", [])
    )
    second_participants = set(
        _read_or_build(second, values).get("participants", [])
    )

    return bool(
        first_participants
        and second_participants
        and len(first_participants & second_participants)
        < values["min_shared_participants"]
    )


def _meaningful_tokens(text, settings):
    stop_words = set(settings["stop_words"])
    noise_prefixes = tuple(settings["noise_prefixes"])
    tokens = set()

    for token in re.findall(r"[\w-]+", text.casefold(), flags=re.UNICODE):
        token = token.strip("_-")

        if len(token) < 4 or token in stop_words:
            continue

        if any(token.startswith(prefix) for prefix in noise_prefixes):
            continue

        tokens.add(token)

    return tokens


def _parse_datetime(value):
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return None

    if not isinstance(value, datetime):
        return None

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def _parse_event_datetime(value):
    """Parse only event times that already contain a reliable timezone."""

    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    if not isinstance(value, datetime) or value.tzinfo is None:
        return None

    return value.astimezone(timezone.utc)


def _parse_event_date(value):
    """Parse an explicit ISO calendar date without inventing a clock time."""

    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None

    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _choose_preferred(first, second):
    if first.get("score", 0) != second.get("score", 0):
        return first if first.get("score", 0) > second.get("score", 0) else second

    def quality(item):
        body = item.get("article_text", "")
        return (
            bool(body),
            bool(item.get("image_url")),
            len(body),
            item.get("source_trust", 0),
        )

    return second if quality(second) > quality(first) else first


def _confirmed_sources(*items_or_sources):
    """Collect distinct source names without counting a source twice."""

    sources = []
    for value in items_or_sources:
        if isinstance(value, str):
            candidates = (value,)
        else:
            candidates = value.get("confirmed_sources") or (
                value.get("source"),
            )
        for source in candidates:
            if source and source not in sources:
                sources.append(source)
    return sources


def _attach_confirmed_sources(item, sources=None):
    item["confirmed_sources"] = _confirmed_sources(
        *(sources or (item,))
    )
