from collectors.html_collector import collect_html


class Response:
    content = b"""
    <article class='card'>
      <h2><a href='/story'>Story title</a></h2>
      <time datetime='Wed, 01 Jan 2026 10:00:00 +0000'></time>
      <p class='summary'>Useful <b>summary</b></p>
    </article>
    """

    def raise_for_status(self):
        return None


def test_declarative_html_collector_builds_shared_contract(monkeypatch):
    monkeypatch.setattr(
        "collectors.html_collector.requests.get",
        lambda *args, **kwargs: Response(),
    )
    source = {
        "name": "HTML Example",
        "url": "https://example.test/news",
        "base_url": "https://example.test",
        "item_selector": "article.card",
        "title_selector": "h2 a",
        "link_selector": "h2 a",
        "date_selector": "time",
        "description_selector": ".summary",
    }

    items = collect_html(source)

    assert items[0]["title"] == "Story title"
    assert items[0]["url"] == "https://example.test/story"
    assert items[0]["description"] == "Useful summary"
    assert items[0]["published_at"].tzinfo is not None

