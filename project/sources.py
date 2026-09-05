"""MMA sources and optional source-specific article hooks."""

from datetime import datetime, timedelta, timezone


now = datetime.now(timezone.utc)

# Stage 1 is deliberately local. Live sources are added only after each feed or
# page has been checked for stable URLs, dates, access, and article extraction.
SOURCES = [
    {
        "name": "MMA Autoposter local fixture",
        "type": "static",
        "enabled": True,
        "items": [
            {
                "title": "UFC официально объявил титульный бой Ислама Махачева",
                "url": "https://example.invalid/mma/makhachev-title-fight",
                "published_at": now - timedelta(hours=2),
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
                "title": "Футбольный клуб представил нового главного тренера",
                "url": "https://example.invalid/sport/football-coach",
                "published_at": now - timedelta(hours=1),
                "description": "Команда готовится к следующему сезону.",
                "article_text": "Клуб провёл пресс-конференцию.",
                "image_url": None,
            },
        ],
    },
]

SOURCE_EXTRACTORS = {}
SOURCE_STOP_MARKERS = {}
