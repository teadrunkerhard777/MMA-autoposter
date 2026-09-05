from types import SimpleNamespace

import feedparser

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
