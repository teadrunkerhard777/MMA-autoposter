from html import escape


SENTENCE_ENDINGS = ".!?"
CLOSING_PUNCTUATION = "»”\"')]}"


def fit_text_to_html_limit(text, max_escaped_length):
    """Trim plain text so its escaped representation fits Telegram."""

    cleaned = "\n\n".join(
        " ".join(paragraph.split())
        for paragraph in (text or "").splitlines()
        if paragraph.strip()
    )

    if not cleaned or max_escaped_length <= 0:
        return ""

    if len(escape(cleaned)) <= max_escaped_length:
        return cleaned

    sentence = _last_complete_sentence(cleaned, max_escaped_length)
    if sentence:
        return sentence

    ellipsis = "…"
    available = max_escaped_length - len(ellipsis)
    low, high = 0, len(cleaned)

    while low < high:
        middle = (low + high + 1) // 2

        if len(escape(cleaned[:middle])) <= available:
            low = middle
        else:
            high = middle - 1

    candidate = cleaned[:low].rstrip()
    word_end = max(candidate.rfind(" "), candidate.rfind("\n"))

    if word_end > 0:
        candidate = candidate[:word_end].rstrip()

    candidate = candidate.rstrip(" ,;:—-")
    return f"{candidate}{ellipsis}" if candidate else ""


def _last_complete_sentence(text, max_escaped_length):
    """Return the last complete sentence that fits, preserving close quotes."""

    last_end = 0
    index = 0
    while index < len(text):
        if text[index] not in SENTENCE_ENDINGS:
            index += 1
            continue

        end = index + 1
        while end < len(text) and text[end] in CLOSING_PUNCTUATION:
            end += 1

        candidate = text[:end].rstrip()
        if len(escape(candidate)) > max_escaped_length:
            break
        last_end = end
        index = end

    return text[:last_end].rstrip() if last_end else ""
