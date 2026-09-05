"""MMA sources and optional source-specific article hooks."""

from datetime import datetime, timedelta, timezone


now = datetime.now(timezone.utc)


def extract_sports_ru_article(soup):
    """Extract Sports.ru's structured body without related-story promos."""

    body = soup.select_one(".structured-body-wrapper")
    if body is None:
        return ""

    paragraphs = []
    for node in body.select("p.sb-paragraph"):
        text = " ".join(node.get_text(" ", strip=True).split())
        links = node.find_all("a")
        is_link_only_promo = (
            len(links) == 1
            and " ".join(links[0].get_text(" ", strip=True).split()) == text
            and "sb-text--bold" in (links[0].get("class") or [])
        )

        if text and not is_link_only_promo:
            paragraphs.append(text)

    return "\n\n".join(paragraphs)


SOURCES = [
    {
        "name": "MMA Autoposter local fixture",
        "type": "static",
        "enabled": False,
        "items": [
            {
                "title": "UFC официально объявил титульный бой Ислама Махачева",
                "url": "https://example.invalid/mma/makhachev-title-fight",
                "published_at": now - timedelta(hours=2),
                "event_at": now + timedelta(hours=36),
                "description": (
                    "Ислам Махачев проведёт титульный бой на ближайшем "
                    "номерном турнире UFC. Имя соперника подтверждено "
                    "официальным анонсом промоушена."
                ),
                "article_text": (
                    "UFC официально объявил следующий титульный бой Ислама "
                    "Махачева. Поединок станет главным событием турнира."
                ),
                "image_url": None,
            },
            {
                "title": "Хамзат Чимаев может получить нового соперника",
                "url": "https://example.invalid/mma/chimaev-rumor",
                "published_at": now - timedelta(hours=4),
                "event_at": now + timedelta(days=5),
                "description": (
                    "По данным журналиста, UFC ведёт переговоры о новом бое. "
                    "Пока официально поединок не подтверждён."
                ),
                "article_text": (
                    "Хамзат Чимаев может вернуться в октагон против нового "
                    "соперника. Стороны обсуждают бой, но UFC его не объявлял."
                ),
                "image_url": None,
            },
            {
                "title": "Боец ACA победил нокаутом в главном бою турнира",
                "url": "https://example.invalid/mma/aca-knockout-result",
                "published_at": now - timedelta(hours=6),
                "event_at": now - timedelta(hours=7),
                "description": (
                    "Поединок завершился нокаутом во втором раунде. "
                    "Победитель укрепил позиции в дивизионе ACA."
                ),
                "article_text": (
                    "Главный бой турнира ACA завершился нокаутом во втором "
                    "раунде. Рефери остановил поединок после серии ударов."
                ),
                "image_url": None,
            },
            {
                "title": "Травма изменила кард турнира UFC",
                "url": "https://example.invalid/mma/ufc-card-injury",
                "published_at": now - timedelta(minutes=40),
                "event_at": now + timedelta(days=5),
                "description": (
                    "Участник снялся с боя из-за травмы. UFC готовит замену "
                    "для карда турнира."
                ),
                "article_text": (
                    "Травма вынудила бойца сняться с турнира UFC. Промоушен "
                    "объявит нового соперника после завершения переговоров."
                ),
                "image_url": None,
            },
            {
                "title": "Женщины в MMA: техника и характер яркой спортсменки",
                "url": "https://example.invalid/mma/women-profile",
                "published_at": now - timedelta(days=30),
                "scheduled_at": now - timedelta(hours=1),
                "content_queue": "evergreen",
                "content_type": "women_mma",
                "description": (
                    "Локальный пример профиля женщины-бойца: спортивные "
                    "достижения, стиль и сильный визуальный образ."
                ),
                "article_text": (
                    "Профиль объединяет проверяемые спортивные факты, "
                    "особенности стиля и яркую визуальную подачу."
                ),
                "image_url": None,
            },
            {
                "title": "Боец дня: путь от дебюта до большого турнира",
                "url": "https://example.invalid/mma/fighter-profile",
                "published_at": now - timedelta(days=30),
                "scheduled_at": now - timedelta(minutes=30),
                "content_queue": "evergreen",
                "content_type": "fighter",
                "description": (
                    "Локальный пример планового профиля бойца с рекордом, "
                    "стилем и ключевыми достижениями."
                ),
                "article_text": (
                    "Плановый материал рассказывает о развитии бойца, его "
                    "сильных сторонах и важных этапах карьеры."
                ),
                "image_url": None,
            },
            {
                "title": "История MMA: материал для вечерней публикации",
                "url": "https://example.invalid/mma/future-history",
                "published_at": now - timedelta(days=30),
                "scheduled_at": now + timedelta(hours=6),
                "content_queue": "evergreen",
                "content_type": "history",
                "description": "Этот материал ещё не должен попасть в выборку.",
                "article_text": "Публикация ожидает своего времени.",
                "image_url": None,
            },
            {
                "title": "Футбольный клуб представил нового главного тренера",
                "url": "https://example.invalid/sport/football-coach",
                "published_at": now - timedelta(hours=1),
                "description": "Команда готовится к следующему сезону.",
                "article_text": "Клуб провёл пресс-конференцию.",
                "image_url": None,
            },
        ],
    },
    {
        "name": "UFC Official News",
        "type": "rss",
        "url": "https://www.ufc.com/rss/news",
        "enabled": False,
        "limit": 20,
        "source_kind": "official_promotion",
        "language": "en",
    },
    {
        "name": "ONE Championship Russian",
        "type": "rss",
        "url": "https://rss.tech.onefc.com/base-russian.xml",
        "enabled": True,
        "limit": 20,
        "source_kind": "official_promotion",
        "language": "ru",
        "translation": "official_ai",
        "feed_timeout": 15,
        "use_feed_content": True,
        "feed_stop_markers": ("Источник",),
    },
    {
        "name": "Sports.ru UFC/MMA",
        "type": "rss",
        "url": "https://www.sports.ru/rss/tags.xml?id=3109101",
        "enabled": True,
        "limit": 15,
        "source_kind": "media",
        "language": "ru",
        "feed_timeout": 15,
        "headers": {"Accept-Language": "ru-RU"},
        "retries": 1,
    },
    {
        "name": "MMA Fighting",
        "type": "rss",
        "url": "https://www.mmafighting.com/rss/index.xml",
        "enabled": False,
        "limit": 20,
        "source_kind": "media",
        "language": "en",
    },
]

SOURCE_EXTRACTORS = {
    "Sports.ru UFC/MMA": extract_sports_ru_article,
}
SOURCE_STOP_MARKERS = {}
