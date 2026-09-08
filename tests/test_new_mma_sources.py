import feedparser

from article.fetcher import (
    clean_article_text,
    extract_article_image_url,
    extract_article_published_at,
    extract_article_text,
)
from collectors.html_collector import collect_html
from collectors.rss_collector import collect_rss
from project.filters import is_relevant
from project.sources import (
    SOURCE_EXTRACTORS,
    SOURCE_IMAGE_EXTRACTORS,
    SOURCE_PUBLISHED_AT_EXTRACTORS,
)


FIGHTTIME_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><item>
  <title>UFC объявил новый бой Ислама Махачева</title>
  <link>https://fighttime.ru/news/item/1.html</link>
  <pubDate>Sun, 06 Sep 2026 10:40:43 +0300</pubDate>
  <description>Официальный анонс UFC.</description>
</item></channel></rss>""".encode()


def test_fighttime_rss_uses_shared_dated_contract(monkeypatch):
    parsed = feedparser.parse(FIGHTTIME_RSS)
    monkeypatch.setattr(
        "collectors.rss_collector.feedparser.parse",
        lambda value: parsed,
    )

    item = collect_rss({
        "name": "FightTime.ru",
        "url": "https://fighttime.ru/rssfeed.feed?type=rss",
    })[0]

    assert item["title"] == "UFC объявил новый бой Ислама Махачева"
    assert item["url"] == "https://fighttime.ru/news/item/1.html"
    assert item["published_at"].isoformat() == "2026-09-06T10:40:43+03:00"
    assert is_relevant(item) is True


def test_fighttime_article_body_and_open_graph_image_are_clean():
    html = """
    <meta property="og:image" content="/images/fighter.webp">
    <div class="itemFullText">
      <p>UFC официально объявил бой Ислама Махачева.</p>
      <p>Поединок пройдет на номерном турнире.</p>
    </div>
    <aside><p>Реклама и другие материалы.</p></aside>
    """

    text = clean_article_text(extract_article_text(
        html,
        "FightTime.ru",
        SOURCE_EXTRACTORS,
    ))

    assert text == (
        "UFC официально объявил бой Ислама Махачева.\n\n"
        "Поединок пройдет на номерном турнире."
    )
    assert "Реклама" not in text
    assert extract_article_image_url(
        html,
        "https://fighttime.ru/news/item/1.html",
        source="FightTime.ru",
        source_extractors=SOURCE_IMAGE_EXTRACTORS,
    ) == "https://fighttime.ru/images/fighter.webp"


def test_fighttime_irrelevant_boxing_is_rejected():
    item = {
        "source": "FightTime.ru",
        "title": "Усик проведет следующий боксерский поединок",
        "description": "Чемпион мира по боксу назвал дату боя.",
    }

    assert is_relevant(item) is False


class ListingResponse:
    content = """
    <div class="news_element">
      <a class="news_element_title" href="news/20260906-0514/mma-story">
        <h3>Валентина Шевченко отказалась от пояса UFC</h3>
      </a>
      <div class="news_element_date">6 сентября 2026</div>
    </div>
    <div class="banner"><a href="/bet">Букмекер</a></div>
    """.encode()

    def raise_for_status(self):
        return None


def test_allboxing_listing_uses_only_mma_cards(monkeypatch):
    monkeypatch.setattr(
        "collectors.html_collector.requests.get",
        lambda *args, **kwargs: ListingResponse(),
    )
    source = {
        "name": "AllBoxing.ru MMA",
        "url": "https://allboxing.ru/mma-news.html",
        "base_url": "https://allboxing.ru/",
        "item_selector": ".news_element",
        "title_selector": ".news_element_title",
        "link_selector": ".news_element_title",
        "date_selector": ".news_element_date",
    }

    items = collect_html(source)

    assert len(items) == 1
    assert items[0]["title"] == "Валентина Шевченко отказалась от пояса UFC"
    assert items[0]["url"] == "https://allboxing.ru/news/20260906-0514/mma-story"


def test_allboxing_article_uses_json_ld_date_body_and_lead_image():
    html = """
    <script type="application/ld+json">
      {"@type":"Article", "datePublished":"2026-09-06T01:14:21+03:00"}
    </script>
    <div class="news_element_image"><img src="/images/shevchenko.jpg"></div>
    <div class="field-name-body">
      <p>Валентина Шевченко отказалась от чемпионского пояса UFC.</p>
      <p>Новая чемпионка определится в следующем бою.</p>
    </div>
    <aside><p>Экспресс с коэффициентом 10+. Получить фрибет.</p></aside>
    """

    text = clean_article_text(extract_article_text(
        html,
        "AllBoxing.ru MMA",
        SOURCE_EXTRACTORS,
    ))

    assert text == (
        "Валентина Шевченко отказалась от чемпионского пояса UFC.\n\n"
        "Новая чемпионка определится в следующем бою."
    )
    assert "Экспресс" not in text
    assert extract_article_published_at(
        html,
        "AllBoxing.ru MMA",
        SOURCE_PUBLISHED_AT_EXTRACTORS,
    ) == "2026-09-06T01:14:21+03:00"
    assert extract_article_image_url(
        html,
        "https://allboxing.ru/news/story",
        source="AllBoxing.ru MMA",
        source_extractors=SOURCE_IMAGE_EXTRACTORS,
    ) == "https://allboxing.ru/images/shevchenko.jpg"


def test_allboxing_betting_material_is_rejected():
    item = {
        "source": "AllBoxing.ru MMA",
        "title": "Прогноз на бой UFC: коэффициенты букмекеров",
        "description": "Экспресс и фрибет для новых игроков.",
    }

    assert is_relevant(item) is False
