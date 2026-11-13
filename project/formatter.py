"""Russian Telegram presentation for the MMA channel."""

import re
from datetime import datetime
from html import escape

from generation.text import fit_text_to_html_limit


MESSAGE_LIMIT = 4000
PHOTO_CAPTION_LIMIT = 1000
VIDEO_CAPTION_LIMIT = 1000

CATEGORY_LABELS = {
    "fight_announcement": "🔥 НОВЫЙ БОЙ",
    "evergreen_fighter": "🥋 БОЕЦ ДНЯ",
    "evergreen_women_mma": "✨ ЖЕНЩИНЫ В MMA",
    "evergreen_matchup": "⚔️ ПРОТИВОСТОЯНИЕ",
    "evergreen_fact": "📊 MMA-ФАКТ",
    "evergreen_history": "📚 ИСТОРИЯ MMA",
}

# Словарь канонических ID бойцов -> русский тег по фамилии
FIGHTER_SURNAME_TAGS = {
    "islam_makhachev": "Махачев",
    "petr_yan": "Ян",
    "khamzat_chimaev": "Чимаев",
    "magomed_ankalaev": "Анкалаев",
    "alexander_volkanovski": "Волкановски",
    "ilia_topuria": "Топурия",
    "alex_pereira": "Перейра",
    "jon_jones": "Джонс",
    "tom_aspinall": "Аспиналл",
    "shavkat_rakhmonov": "Рахмонов",
    "conor_mcgregor": "Макгрегор",
    "arman_tsarukyan": "Царукян",
    "mauricio_ruffy": "Руффи",
    "umar_nurmagomedov": "Нурмагомедов",
    "song_yadong": "Ядун",
    "dan_hooker": "Хукер",
    "salahdine_parnasse": "Парнасс",
    "michael_page": "Пейдж",
    "nursulton_ruziboev": "Рузибоев",
    "valentina_shevchenko": "Шевченко",
    "kayla_harrison": "Харрисон",
    "zhang_weili": "Вэйли",
    "mackenzie_dern": "Дерн",
    "natalia_silva": "Силва",
    "manon_fiorot": "Фиоро",
    "alexa_grasso": "Грассо",
    "merab_dvalishvili": "Двалишвили",
    "erin_blanchfield": "Бланчфилд",
    "sean_strickland": "Стрикленд",
    "rose_namajunas": "Намаюнас",
    "charles_oliveira": "Оливейра",
    "tatiana_suarez": "Суарес",
    "yan_xiaonan": "Сяонань",
    "justin_gaethje": "Гейджи",
    "maycee_barber": "Барбер",
    "denise_gomes": "Гомес",
    "tracy_cortez": "Кортес",
    "fatima_kline": "Клайн",
    "amanda_nunes": "Нуньес",
    "jasmine_jasudavicius": "Ясудавичюс",
    "ciryl_gane": "Ган",
    "julianna_pena": "Пенья",
    "joshua_van": "Ван",
    "raquel_pennington": "Пеннингтон",
}

# Поиск по основам фамилий в тексте/заголовке (с учётом русских падежей)
SURNAME_STEMS = (
    ("махачев", "Махачев"),
    ("петр ян", "Ян"),
    ("пётр ян", "Ян"),
    ("петра ян", "Ян"),
    ("петру ян", "Ян"),
    ("чимаев", "Чимаев"),
    ("анкалаев", "Анкалаев"),
    ("волкановск", "Волкановски"),
    ("топури", "Топурия"),
    ("перейр", "Перейра"),
    ("джонс", "Джонс"),
    ("аспиналл", "Аспиналл"),
    ("рахмонов", "Рахмонов"),
    ("макгрегор", "Макгрегор"),
    ("царукян", "Царукян"),
    ("нурмагомедов", "Нурмагомедов"),
    ("ядун", "Ядун"),
    ("парнасс", "Парнасс"),
    ("шевченк", "Шевченко"),
    ("харрисон", "Харрисон"),
    ("вэйли", "Вэйли"),
    ("дерн", "Дерн"),
    ("силв", "Силва"),
    ("фиоро", "Фиоро"),
    ("грассо", "Грассо"),
    ("двалишвили", "Двалишвили"),
    ("бланчфилд", "Бланчфилд"),
    ("стрикленд", "Стрикленд"),
    ("намаюнас", "Намаюнас"),
    ("оливейр", "Оливейра"),
    ("суарес", "Суарес"),
    ("сяонан", "Сяонань"),
    ("гейджи", "Гейджи"),
    ("барбер", "Барбер"),
    ("гомес", "Гомес"),
    ("кортес", "Кортес"),
    ("клайн", "Клайн"),
    ("нуньес", "Нуньес"),
    ("ясудавичюс", "Ясудавичюс"),
    ("сирил ган", "Ган"),
    ("сирила ган", "Ган"),
    ("пенья", "Пенья"),
    ("джошуа ван", "Ван"),
    ("пеннингтон", "Пеннингтон"),
    ("евлоев", "Евлоев"),
    ("павлович", "Павлович"),
    ("волков", "Волков"),
    ("копылов", "Копылов"),
    ("шара булл", "Магомедов"),
    ("шарабутдин", "Магомедов"),
    ("порью", "Порье"),
    ("порье", "Порье"),
    ("холлоуэ", "Холлоуэй"),
    ("дю плесси", "ДюПлесси"),
    ("адесань", "Адесанья"),
    ("прохазк", "Прохазка"),
    ("о'мэлли", "ОМэлли"),
    ("омэлли", "ОМэлли"),
    ("пантож", "Пантожа"),
    ("мокаев", "Мокаев"),
    ("солдич", "Солдич"),
    ("усманов", "Усманов"),
    ("усман", "Усман"),
    ("ковин", "Ковингтон"),
    ("белал", "Мухаммад"),
)


def format_post(news_item):
    """Build one HTML-safe Telegram text message."""

    return _format(news_item, MESSAGE_LIMIT)


def format_photo_caption(news_item):
    """Build one HTML-safe Telegram photo caption."""

    return _format(news_item, PHOTO_CAPTION_LIMIT)


def format_video_caption(video_item):
    """Build a compact HTML caption for the recurring video feature."""

    title = escape(str(video_item.get("title") or "Момент дня")[:300])
    source = escape(str(video_item.get("source") or "Источник не указан"))
    source_url = escape(str(video_item.get("source_url") or ""), quote=True)
    header = f"🎬 <b>{title}</b>"
    source_line = (
        f'📰 <a href="{source_url}">{source}</a>'
        if source_url
        else f"📰 {source}"
    )
    footer = f"{source_line}\n\n#MMAVideo"
    note = fit_text_to_html_limit(
        video_item.get("note") or "",
        max(0, VIDEO_CAPTION_LIMIT - len(header) - len(footer) - 4),
    )
    blocks = [header]
    if note:
        blocks.append(escape(note))
    blocks.append(footer)
    return "\n\n".join(blocks)


def _format(news_item, limit):
    title = escape(str(news_item.get("title") or "Без заголовка")[:500])
    source = escape(str(news_item.get("source") or "Источник не указан"))
    url = escape(str(news_item.get("url") or ""), quote=True)
    category = news_item.get("event_category")
    label = CATEGORY_LABELS.get(category, "")
    tags = _hashtags(news_item)

    header_blocks = []
    if news_item.get("is_rumor"):
        header_blocks.append(
            "👀 <b>СЛУХ</b>\nПока официально не подтверждено."
        )
    header_blocks.append(
        f"{label}\n\n<b>{title}</b>" if label else f"<b>{title}</b>"
    )

    footer = (
        f"{_date_line(news_item)}\n"
        f"📰 {source}\n\n"
        f'🔗 <a href="{url}">Источник</a>'
    )
    if tags:
        footer = f"{footer}\n\n{tags}"

    fixed = "\n\n".join((*header_blocks, footer))
    body = news_item.get("article_text") or news_item.get("description", "")
    body = fit_text_to_html_limit(body, max(0, limit - len(fixed) - 2))

    blocks = [*header_blocks]
    if body:
        blocks.append(escape(body))
    blocks.append(footer)
    return "\n\n".join(blocks)


def _hashtags(news_item):
    """Return a single hashtag with the main fighter's surname."""

    for key in ("matched_fighters", "event_participants"):
        for fighter_id in news_item.get(key) or []:
            surname = FIGHTER_SURNAME_TAGS.get(fighter_id)
            if surname:
                return f"#{surname}"

    title_and_desc = (
        f"{news_item.get('title') or ''} "
        f"{news_item.get('description') or ''}"
    ).casefold()

    for stem, surname in SURNAME_STEMS:
        if stem in title_and_desc:
            return f"#{surname}"

    # Попытка извлечь "Имя Фамилия" с заглавных букв из заголовка
    raw_title = str(news_item.get("title") or "")
    name_match = re.search(
        r"\b([А-ЯЁ][а-яё]{2,})\s+([А-ЯЁ][а-яё]{2,})\b",
        raw_title,
    )
    if name_match:
        stop_titles = {"Новый", "Главный", "Бывший", "Турнир", "Боец", "Чемпион", "Женщины", "История"}
        first_word, second_word = name_match.group(1), name_match.group(2)
        if first_word not in stop_titles and second_word not in stop_titles:
            return f"#{second_word}"

    return "#MMA"


def _format_date(value):
    if not isinstance(value, datetime) or value.tzinfo is None:
        return "Дата не указана"
    return value.strftime("%d.%m.%Y %H:%M %Z")


def _format_calendar_date(value):
    if not isinstance(value, datetime) or value.tzinfo is None:
        return "Дата не указана"
    return value.strftime("%d.%m.%Y")


def _date_line(news_item):
    event_at = news_item.get("event_at")
    if isinstance(event_at, datetime):
        return f"🥊 Событие: {_format_date(event_at)}"

    event_date = news_item.get("event_date")
    if isinstance(event_date, str):
        try:
            parsed_event_date = datetime.strptime(
                event_date,
                "%Y-%m-%d",
            )
        except ValueError:
            parsed_event_date = None

        if parsed_event_date is not None:
            return (
                "🥊 Событие: "
                f"{parsed_event_date.strftime('%d.%m.%Y')} "
                "(время уточняется)"
            )

    if news_item.get("content_queue") == "evergreen":
        return f"📅 По расписанию: {_format_date(news_item.get('scheduled_at'))}"

    return (
        "📅 Материал: "
        f"{_format_calendar_date(news_item.get('published_at'))}"
    )
