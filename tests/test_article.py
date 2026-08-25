from article.fetcher import (
    clean_article_text,
    extract_article_image_url,
    extract_article_text,
)


def test_generic_article_extraction_prefers_article_container():
    html = """
    <p>Navigation paragraph</p>
    <article><p>Useful first paragraph.</p><p>Useful second paragraph.</p></article>
    <footer><p>Footer paragraph</p></footer>
    """

    text = extract_article_text(html)

    assert "Useful first" in text
    assert "Navigation" not in text
    assert "Footer" not in text


def test_source_specific_extractor_is_isolated():
    html = "<article><p>Generic body</p></article><div class='special'>Special body</div>"

    def special(soup):
        return soup.select_one(".special").get_text(strip=True)

    registry = {"Special Source": special}

    assert extract_article_text(html, "Special Source", registry) == "Special body"
    assert extract_article_text(html, "Other Source", registry) == "Generic body"


def test_source_stop_marker_does_not_affect_other_sources():
    text = "Useful paragraph\n\nNewsletter signup\n\nFooter"
    markers = {"Special Source": ("newsletter signup",)}

    assert clean_article_text(text, "Special Source", markers) == "Useful paragraph"
    assert "Footer" in clean_article_text(text, "Other Source", markers)


def test_image_metadata_prefers_open_graph_and_resolves_relative_url():
    html = """
    <meta property='og:image' content='/images/main.jpg'>
    <meta name='twitter:image' content='https://cdn.test/twitter.jpg'>
    """

    assert extract_article_image_url(html, "https://news.test/story") == "https://news.test/images/main.jpg"


def test_image_metadata_falls_back_to_twitter():
    html = "<meta name='twitter:image' content='https://cdn.test/image.jpg'>"
    assert extract_article_image_url(html, "https://news.test") == "https://cdn.test/image.jpg"

