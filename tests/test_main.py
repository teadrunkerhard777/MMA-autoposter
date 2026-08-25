from main import load_article_data


def test_one_html_request_supplies_text_and_image(monkeypatch):
    calls = []
    html = """
    <article><p>Article body</p></article>
    <meta property='og:image' content='/photo.jpg'>
    """

    def fetch(url):
        calls.append(url)
        return html

    monkeypatch.setattr("main.fetch_article_html", fetch)
    item = {
        "title": "Story",
        "url": "https://example.test/story",
        "source": "Example",
    }

    load_article_data([item])

    assert calls == ["https://example.test/story"]
    assert item["article_text"] == "Article body"
    assert item["image_url"] == "https://example.test/photo.jpg"


def test_preloaded_article_data_skips_http(monkeypatch):
    monkeypatch.setattr("main.fetch_article_html", lambda url: pytest.fail("unexpected request"))
    item = {
        "url": "https://example.test/story",
        "article_text": "Already loaded",
        "image_url": None,
    }

    load_article_data([item])


import pytest

