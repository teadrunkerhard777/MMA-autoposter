from types import SimpleNamespace

import feedparser
import requests

from collectors.rss_collector import collect_rss


RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>MMA Test</title>
    <item>
      <title>First UFC story</title>
      <link>https://example.test/first</link>
      <pubDate>Sat, 05 Sep 2026 10:32:00 +0300</pubDate>
      <description>First summary</description>
    </item>
    <item>
      <title>Second UFC story</title>
      <link>https://example.test/second</link>
      <pubDate>Sat, 05 Sep 2026 09:00:00 +0300</pubDate>
      <description>Second summary</description>
    </item>
  </channel>
</rss>
"""


def source(**overrides):
    values = {
        "name": "MMA RSS",
        "type": "rss",
        "url": "https://example.test/feed.xml",
    }
    values.update(overrides)
    return values


def test_rss_collector_builds_dated_direct_items(monkeypatch):
    parsed = feedparser.parse(RSS)
    monkeypatch.setattr(
        "collectors.rss_collector.feedparser.parse",
        lambda url: parsed,
    )

    items = collect_rss(source())

    assert [item["url"] for item in items] == [
        "https://example.test/first",
        "https://example.test/second",
    ]
    assert all(item["published_at"].tzinfo is not None for item in items)


def test_rss_collector_honors_source_limit(monkeypatch):
    parsed = feedparser.parse(RSS)
    monkeypatch.setattr(
        "collectors.rss_collector.feedparser.parse",
        lambda url: parsed,
    )

    items = collect_rss(source(limit=1))

    assert [item["title"] for item in items] == ["First UFC story"]


def test_rss_collector_isolates_expected_parser_failure(monkeypatch, capsys):
    def fail(url):
        raise OSError("temporary source failure")

    monkeypatch.setattr("collectors.rss_collector.feedparser.parse", fail)

    assert collect_rss(source()) == []
    assert "RSS warning (MMA RSS): OSError" in capsys.readouterr().out


def test_rss_collector_keeps_valid_entries_from_bozo_feed(monkeypatch, capsys):
    parsed = feedparser.parse(RSS)
    parsed.bozo = True
    parsed.bozo_exception = ValueError("trailing invalid data")
    monkeypatch.setattr(
        "collectors.rss_collector.feedparser.parse",
        lambda url: parsed,
    )

    items = collect_rss(source())

    assert len(items) == 2
    assert "RSS warning (MMA RSS)" in capsys.readouterr().out


def test_rss_collector_accepts_empty_feed(monkeypatch):
    parsed = SimpleNamespace(entries=[], bozo=False)
    monkeypatch.setattr(
        "collectors.rss_collector.feedparser.parse",
        lambda url: parsed,
    )

    assert collect_rss(source()) == []


def test_rss_collector_can_preload_full_feed_content_and_image(monkeypatch):
    rss = b"""<?xml version="1.0" encoding="UTF-8"?>
    <rss xmlns:media="http://search.yahoo.com/mrss/" version="2.0">
      <channel><item>
        <title>ONE MMA story</title>
        <link>https://example.test/story</link>
        <pubDate>Sat, 05 Sep 2026 10:32:00 +0300</pubDate>
        <description>Summary</description>
        <content:encoded xmlns:content="http://purl.org/rss/1.0/modules/content/">
          <![CDATA[<p>First paragraph.</p><p>Second paragraph.</p><p>Source</p><p>Footer</p>]]>
        </content:encoded>
        <media:content url="/images/cover.jpg" />
      </item></channel>
    </rss>"""
    parsed = feedparser.parse(rss)
    monkeypatch.setattr(
        "collectors.rss_collector.feedparser.parse",
        lambda url: parsed,
    )

    items = collect_rss(
        source(
            use_feed_content=True,
            feed_stop_markers=("Source",),
        )
    )

    assert items[0]["article_text"] == "First paragraph.\n\nSecond paragraph."
    assert items[0]["image_url"] == "https://example.test/images/cover.jpg"


def test_rss_collector_leaves_feed_content_opt_in(monkeypatch):
    parsed = feedparser.parse(RSS)
    monkeypatch.setattr(
        "collectors.rss_collector.feedparser.parse",
        lambda url: parsed,
    )

    item = collect_rss(source())[0]

    assert "article_text" not in item
    assert "image_url" not in item


def test_rss_collector_bounds_live_feed_request(monkeypatch):
    class Response:
        content = RSS

        def raise_for_status(self):
            return None

    request = {}

    def get(url, **kwargs):
        request.update(url=url, **kwargs)
        return Response()

    monkeypatch.setattr("collectors.rss_collector.requests.get", get)

    items = collect_rss(
        source(
            feed_timeout=12,
            headers={"Accept-Language": "ru-RU"},
        )
    )

    assert len(items) == 2
    assert request == {
        "url": "https://example.test/feed.xml",
        "headers": {"Accept-Language": "ru-RU"},
        "timeout": 12.0,
    }


def test_rss_collector_isolates_feed_timeout(monkeypatch, capsys):
    def timeout(*args, **kwargs):
        raise requests.ConnectTimeout("slow feed")

    monkeypatch.setattr(
        "collectors.rss_collector.requests.get",
        timeout,
    )

    assert collect_rss(source(feed_timeout=1)) == []
    assert "ConnectTimeout" in capsys.readouterr().out
