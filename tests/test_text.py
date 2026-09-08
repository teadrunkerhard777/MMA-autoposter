from generation.text import fit_text_to_html_limit


def test_truncation_ends_at_last_complete_sentence_without_ellipsis():
    text = "Первое предложение. Второе предложение не помещается целиком."

    assert fit_text_to_html_limit(text, len("Первое предложение.")) == (
        "Первое предложение."
    )


def test_truncation_preserves_closing_quote_after_sentence_end():
    text = "Он сказал: «Это важно!» Затем продолжил длинную мысль."
    complete = "Он сказал: «Это важно!»"

    assert fit_text_to_html_limit(text, len(complete)) == complete


def test_truncation_uses_word_boundary_fallback_without_dangling_punctuation():
    text = "Длинная мысль, которая не успевает закончиться вовремя"

    assert fit_text_to_html_limit(text, 18) == "Длинная мысль…"


def test_naturally_fitting_text_is_not_changed_or_ellipsized():
    text = "Готовое предложение."

    assert fit_text_to_html_limit(text, 100) == text
