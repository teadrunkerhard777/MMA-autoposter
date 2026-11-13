"""One-click updater for Fighter of the Day module, cards, and Wikimedia photos."""

from __future__ import annotations

import json
import urllib.parse
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent
FIGHTERS_DIR = ROOT / "project" / "content" / "fighters"
FIGHTER_OF_DAY_PY = ROOT / "project" / "fighter_of_day.py"

HEADERS = {
    "User-Agent": "MMAAutoposterUpdater/1.0 (https://github.com/teadrunkerhard777/MMA-autoposter)"
}


# 1. ОБНОВЛЕННЫЙ КОД project/fighter_of_day.py (с ротацией всех абзацев и защитой от повторов)
UPDATED_FIGHTER_OF_DAY_CODE = '''"""Deterministic Fighter of the Day rotation and dry-run simulation."""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

from project.fighter_cards import (
    load_fighter_cards,
    validate_fighter_card,
    validate_fighter_image,
)


HISTORY_KIND = "fighter_of_day"
DEFAULT_GENDER = "male"


def eligible_fighters(cards: list[dict], project_root: Path | None = None) -> list[dict]:
    """Return enabled cards whose content and local image both validate."""
    return [
        card
        for card in cards
        if card.get("enabled")
        and not validate_fighter_card(card)
        and not validate_fighter_image(card, project_root)
    ]


def select_next_fighter(
    cards: list[dict],
    history: list[dict],
    selected_at: datetime,
    project_root: Path | None = None,
) -> dict | None:
    """Select one unused fighter while preserving alternation when possible."""
    available = eligible_fighters(cards, project_root)
    if not available:
        return None

    fighter_history = [entry for entry in history if entry.get("kind") == HISTORY_KIND]
    cycle = max((entry.get("cycle", 1) for entry in fighter_history), default=1)
    used = {
        entry.get("fighter_id")
        for entry in fighter_history
        if entry.get("cycle") == cycle
    }
    unused = [card for card in available if card["id"] not in used]
    started_new_cycle = not unused
    if started_new_cycle:
        cycle += 1
        unused = available

    last_gender = fighter_history[-1].get("gender") if fighter_history else None
    preferred_gender = "female" if last_gender == "male" else DEFAULT_GENDER
    if last_gender == "female":
        preferred_gender = "male"

    preferred = [card for card in unused if card["gender"] == preferred_gender]
    fallback_used = not preferred
    candidates = preferred or unused
    card = candidates[0]
    topic_id = _select_topic(card, fighter_history)
    history_entry = {
        "kind": HISTORY_KIND,
        "fighter_id": card["id"],
        "selected_at": selected_at.isoformat(),
        "cycle": cycle,
        "content_topic": topic_id,
        "gender": card["gender"],
    }
    return {
        "card": card,
        "fighter_id": card["id"],
        "gender": card["gender"],
        "image_path": card["image"]["local_path"],
        "image_valid": True,
        "cycle": cycle,
        "content_topic": topic_id,
        "fallback_used": fallback_used,
        "started_new_cycle": started_new_cycle,
        "history_entry": history_entry,
        "post_html": format_fighter_post(card, topic_id),
    }


def simulate_fighter_days(
    days: int,
    cards: list[dict] | None = None,
    production_history: list[dict] | None = None,
    start_at: datetime | None = None,
    project_root: Path | None = None,
) -> list[dict]:
    """Run consecutive selections against isolated in-memory history."""
    simulation_history = deepcopy(production_history or [])
    current_time = start_at or datetime.now(timezone.utc)
    results = []
    seen_by_cycle: dict[int, set[str]] = {}

    for day in range(1, days + 1):
        selected = select_next_fighter(
            cards if cards is not None else load_fighter_cards(),
            simulation_history,
            current_time + timedelta(days=day - 1),
            project_root,
        )
        if selected is None:
            break
        cycle_seen = seen_by_cycle.setdefault(selected["cycle"], set())
        selected["day"] = day
        selected["repeated"] = selected["fighter_id"] in cycle_seen
        cycle_seen.add(selected["fighter_id"])
        results.append(selected)
        simulation_history.append(selected["history_entry"])
    return results


def format_fighter_post(card: dict, topic_id: str | None = None) -> str:
    """Build the agreed compact Telegram HTML post without duplicate statements."""
    stats = card["stats"]
    record = stats["record"]
    wins_by = stats["wins_by"]
    streak = stats.get("current_streak") or {}
    streak_text = _streak_text(streak)
    title_text = _title_or_rank(card)

    angle_index = _angle_index(card, topic_id)
    career_list = card.get("career_story") or []
    style_list = card.get("fighting_style") or []

    career_line = career_list[angle_index % len(career_list)] if career_list else ""
    style_line = style_list[angle_index % len(style_list)] if style_list else ""
    positioning = card["positioning"]

    composed_context = " ".join([title_text, positioning, career_line, style_line])
    fact = _fact_for_topic(card, topic_id, composed_context)

    blocks = [
        f"🥊 <b>БОЕЦ ДНЯ — {escape(card['name_ru'].upper())}</b>",
        (
            f"📊 <b>{record['wins']}–{record['losses']}–{record['draws']}</b>"
            f"{escape(streak_text)}\\n"
            f"🏆 {escape(title_text)}\\n"
            f"⚡ KO/TKO: {wins_by['ko_tko']} · Сабмишены: {wins_by['submission']}"
        ),
        escape(positioning),
    ]
    if career_line and not _is_redundant(career_line, positioning):
        blocks.append(escape(career_line))
    if style_line and not _is_redundant(style_line, f"{positioning} {career_line}"):
        blocks.append(escape(style_line))
    if fact:
        blocks.append(f"💡 <b>Интересный факт:</b> {escape(fact)}")
    blocks.append(f"#БоецДня #MMA #{escape(card['promotion'].upper())}")
    return "\\n\\n".join(blocks)


def _angle_index(card: dict, topic_id: str | None) -> int:
    angles = card.get("angles") or []
    for idx, angle in enumerate(angles):
        if angle.get("id") == topic_id:
            return idx
    return 0


def _is_redundant(candidate: str, existing_text: str) -> bool:
    """Check if candidate sentence repeats the same core statement."""
    cand_norm = candidate.strip().casefold().rstrip(".")
    exist_norm = existing_text.casefold()
    if not cand_norm:
        return True
    if cand_norm in exist_norm:
        return True
    words = [w.strip(".,!?:;«»()—-") for w in cand_norm.split() if len(w) > 4]
    if not words:
        return False
    overlap = sum(1 for w in words if w in exist_norm) / len(words)
    return overlap >= 0.72


def _select_topic(card: dict, history: list[dict]) -> str | None:
    topic_ids = [angle.get("id") for angle in card.get("angles", []) if angle.get("id")]
    if not topic_ids:
        return None
    previous = [
        entry.get("content_topic")
        for entry in history
        if entry.get("fighter_id") == card["id"]
    ]
    for topic_id in topic_ids:
        if topic_id not in previous:
            return topic_id
    return topic_ids[len(previous) % len(topic_ids)]


def _fact_for_topic(card: dict, topic_id: str | None, existing_text: str = "") -> str:
    facts = {fact["id"]: fact["text"] for fact in card.get("facts", [])}
    angle = next(
        (item for item in card.get("angles", []) if item.get("id") == topic_id),
        None,
    )
    ordered_candidates = []
    if angle:
        for fact_id in angle.get("fact_ids", []):
            if fact_id in facts:
                ordered_candidates.append(facts[fact_id])
    for text in facts.values():
        if text not in ordered_candidates:
            ordered_candidates.append(text)

    for candidate in ordered_candidates:
        if not existing_text or not _is_redundant(candidate, existing_text):
            return candidate
    return ordered_candidates[0] if ordered_candidates else ""


def _streak_text(streak: dict) -> str:
    count = streak.get("count")
    if not isinstance(count, int) or count <= 0:
        return ""
    forms = (
        ("победа", "победы", "побед")
        if streak.get("type") == "win"
        else ("поражение", "поражения", "поражений")
    )
    label = _russian_count_form(count, forms)
    return f" · {count} {label}"


def _russian_count_form(count: int, forms: tuple[str, str, str]) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return forms[0]
    if count % 10 in {2, 3, 4} and count % 100 not in {12, 13, 14}:
        return forms[1]
    return forms[2]


def _title_or_rank(card: dict) -> str:
    current = card.get("titles", {}).get("current", [])
    if current:
        return current[0]["name_ru"]
    rank = card.get("stats", {}).get("promotion_rank")
    if isinstance(rank, int):
        return f"№{rank} рейтинга {card['promotion']}"
    former = card.get("titles", {}).get("former", [])
    if former:
        return former[0]["name_ru"]
    return f"{card['promotion']} · {card['weight_class']}"


def simulation_table(results: list[dict]) -> str:
    """Return a readable fixed-width report for a dry-run sequence."""
    header = "Day | Fighter | Gender | Image valid | Cycle | Repeated? | Fallback used?"
    rows = [header, "-" * len(header)]
    for item in results:
        rows.append(
            f"{item['day']:>3} | {item['card']['name_ru']} | {item['gender']} | "
            f"yes | {item['cycle']} | {'yes' if item['repeated'] else 'no'} | "
            f"{'yes' if item['fallback_used'] else 'no'}"
        )
    return "\\n".join(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate Fighter of the Day rotation")
    parser.add_argument("--days", type=int, default=15)
    args = parser.parse_args()
    print(simulation_table(simulate_fighter_days(max(0, args.days))))


if __name__ == "__main__":
    main()
'''


# 2. ТОЧЕЧНЫЕ ОБНОВЛЕНИЯ СУЩЕСТВУЮЩИХ БОЙЦОВ (актуализация на ноябрь 2026 + устранение повторов)
CARD_PATCHES = {
    "petr_yan": {
        "positioning": "Двукратный чемпион UFC в легчайшем весе, который разбирает элиту дивизиона за счёт эталонного бокса, смены стоек и нарастающего темпа в чемпионских раундах.",
        "career_story": [
            "Пришёл в UFC в 2018 году в статусе чемпиона ACB и прошёл путь через два полноценных титульных цикла.",
            "В октябре 2026 года на турнире в Абу-Даби повторно победил Мераба Двалишвили, защитив чемпионский пояс и доведя победную серию до пяти боёв."
        ],
        "fighting_style": [
            "Высокий блок, жёсткий джеб из обеих стоек и многоударные боксёрские комбинации с акцентом на корпус.",
            "Надёжная защита от тейкдаунов в сочетании с подсечками и силовыми контрпанчами на выходе из клинча."
        ],
        "titles": {
            "current": [
                {
                    "organization": "UFC",
                    "name_ru": "Чемпион UFC в легчайшем весе",
                    "division": "легчайший вес",
                    "won_at": "2025-12",
                    "defenses": 1,
                    "source_ids": ["ufc_profile"]
                }
            ]
        },
        "stats": {
            "record": {"wins": 21, "losses": 5, "draws": 0, "no_contests": 0},
            "wins_by": {"ko_tko": 7, "submission": 1, "decision": 13},
            "current_streak": {"type": "win", "count": 5},
            "promotion_rank": None,
            "pound_for_pound_rank": 3,
            "verified_at": "2026-11-13",
            "source_ids": ["ufc_profile", "ufc_rankings"]
        },
        "facts": [
            {"id": "fact_1", "text": "В юности получил звание мастера спорта по боксу и начинал тренироваться в Дудинке на севере Красноярского края.", "source_ids": ["ufc_profile"]},
            {"id": "fact_2", "text": "За два пятираундовых боя против Мераба Двалишвили отразил более 90% попыток переводов грузинского борца.", "source_ids": ["ufc_profile"]},
            {"id": "fact_3", "text": "Прозвище No Mercy («Без пощады») закрепилось за ним ещё со времён выступлений в сибирских лигах и ACB.", "source_ids": ["ufc_profile"]},
            {"id": "fact_4", "text": "Владеет одним из лучших показателей в истории легчайшего веса UFC по количеству акцентированных попаданий и нокдаунов.", "source_ids": ["ufc_profile"]},
            {"id": "fact_5", "text": "Во время учёбы в Омске подрабатывал охранником и проводил первые поединки за минимальные гонорары.", "source_ids": ["ufc_profile"]},
            {"id": "fact_6", "text": "В октябре 2026 года установил личный рекорд точности значимых ударов в титульном бою (56,1%).", "source_ids": ["ufc_profile"]}
        ]
    },
    "merab_dvalishvili": {
        "positioning": "Рекордсмен UFC по тейкдаунам и экс-чемпион легчайшего веса, превративший феноменальное кардио и непрерывный прессинг в визитную карточку.",
        "career_story": [
            "Переехал из Тбилиси в США ради мечты о UFC и после двух спорных поражений на старте выдал историческую серию из 13 побед подряд.",
            "В 2025 году провёл три успешные защиты титула за один календарный год, прежде чем дважды встретиться в клетке с Петром Яном."
        ],
        "stats": {
            "record": {"wins": 21, "losses": 6, "draws": 0, "no_contests": 0},
            "wins_by": {"ko_tko": 3, "submission": 2, "decision": 16},
            "current_streak": {"type": "loss", "count": 2},
            "promotion_rank": 1,
            "pound_for_pound_rank": 9,
            "verified_at": "2026-11-13",
            "source_ids": ["ufc_profile", "ufc_rankings"]
        },
        "facts": [
            {"id": "fact_1", "text": "Первым в истории UFC преодолел отметку в 100 успешных тейкдаунов, обойдя легендарного Жоржа Сен-Пьера.", "source_ids": ["ufc_profile"]},
            {"id": "fact_2", "text": "Первые годы жизни в Нью-Йорке совмещал ежедневные тренировки в зале Serra-Longo с тяжёлой работой на стройке.", "source_ids": ["ufc_profile"]},
            {"id": "fact_3", "text": "В одном лишь октябрьском бою 2026 года в Абу-Даби предпринял рекордные 58 попыток прохода в ноги за 25 минут.", "source_ids": ["ufc_profile"]},
            {"id": "fact_4", "text": "В 2025 году повторил редчайшее достижение чемпионов UFC, защитив пояс трижды менее чем за двенадцать месяцев.", "source_ids": ["ufc_profile"]},
            {"id": "fact_5", "text": "До перехода в смешанные единоборства занимался грузинской национальной борьбой чидаоба и боевым самбо.", "source_ids": ["ufc_profile"]},
            {"id": "fact_6", "text": "Даже в поединках без досрочного финиша выбрасывает свыше 350 ударов за пять раундов.", "source_ids": ["ufc_profile"]}
        ]
    },
    "alexander_volkanovski": {
        "positioning": "Двукратный чемпион UFC в полулёгком весе и эталон тактического интеллекта, переигравший несколько поколений топ-претендентов.",
        "career_story": [
            "Начал карьеру в 2012 году после выступлений в полупрофессиональном регби и доминировал в первом титульном цикле с пятью защитами.",
            "Вернул пояс в 2025 году, а в 2026-м дважды защитил его — в реванше с Диего Лопесом в Сиднее и против непобеждённого Мовсара Евлоева на UFC 333 в Абу-Даби."
        ],
        "titles": {
            "current": [
                {
                    "organization": "UFC",
                    "name_ru": "Чемпион UFC в полулёгком весе",
                    "division": "полулёгкий вес",
                    "won_at": "2025-04",
                    "defenses": 2,
                    "source_ids": ["ufc_profile"]
                }
            ]
        },
        "stats": {
            "record": {"wins": 29, "losses": 4, "draws": 0, "no_contests": 0},
            "wins_by": {"ko_tko": 13, "submission": 3, "decision": 13},
            "current_streak": {"type": "win", "count": 3},
            "promotion_rank": None,
            "pound_for_pound_rank": 2,
            "verified_at": "2026-11-13",
            "source_ids": ["ufc_profile", "ufc_rankings"]
        },
        "facts": [
            {"id": "fact_1", "text": "Во время карьеры в регби-лиг при росте 168 см выходил на поле с весом около 97 кг (214 фунтов).", "source_ids": ["ufc_profile"]},
            {"id": "fact_2", "text": "При росте 168 см обладает внушительным размахом рук — 181,5 см (71,5 дюйма), что помогает контролировать рослых ударников.", "source_ids": ["ufc_profile"]},
            {"id": "fact_3", "text": "В октябре 2026 года в 38 лет нанёс первое поражение в карьере непобеждённому Мовсару Евлоеву (20–0 на момент боя).", "source_ids": ["ufc_profile"]},
            {"id": "fact_4", "text": "Суммарно выиграл восемь титульных боёв в полулёгком дивизионе UFC.", "source_ids": ["ufc_profile"]},
            {"id": "fact_5", "text": "Вне октагона ведёт популярное кулинарное шоу Cooking With Volk и увлекается барбекю.", "source_ids": ["ufc_profile"]},
            {"id": "fact_6", "text": "Начинал заниматься греко-римской борьбой в 12 лет и дважды выигрывал национальное первенство Австралии среди юниоров.", "source_ids": ["ufc_profile"]}
        ]
    },
    "natalia_silva": {
        "positioning": "Действующая чемпионка UFC в наилегчайшем весе: скоростная ударница из Бразилии, не знающая поражений в октагоне.",
        "career_story": [
            "Начала выступать в 2015 году и после непростого старта в региональных лигах (3–4–1) выдала феноменальную серию из 15 побед подряд.",
            "В октябре 2026 года на турнире UFC 332 победила Ван Цун и завоевала пояс чемпионки UFC, доведя свой рекорд в организации до 9–0."
        ],
        "titles": {
            "current": [
                {
                    "organization": "UFC",
                    "name_ru": "Чемпионка UFC в наилегчайшем весе",
                    "division": "женский наилегчайший вес",
                    "won_at": "2026-10",
                    "defenses": 0,
                    "source_ids": ["ufc_profile"]
                }
            ]
        },
        "stats": {
            "record": {"wins": 21, "losses": 5, "draws": 1, "no_contests": 0},
            "wins_by": {"ko_tko": 5, "submission": 7, "decision": 9},
            "current_streak": {"type": "win", "count": 15},
            "promotion_rank": None,
            "pound_for_pound_rank": 3,
            "verified_at": "2026-11-13",
            "source_ids": ["ufc_profile", "ufc_rankings"]
        },
        "facts": [
            {"id": "fact_1", "text": "Родом из небольшого шахтёрского города Тимотеу в штате Минас-Жерайс и начинала путь с секции тхэквондо.", "source_ids": ["ufc_profile"]},
            {"id": "fact_2", "text": "Шесть из семи своих побед сабмишенами одержала рычагом локтя (армбаром).", "source_ids": ["ufc_profile"]},
            {"id": "fact_3", "text": "На пути к титулу поочерёдно прошла экс-чемпионок Джессику Андраде, Алексу Грассо и Роуз Намаюнас.", "source_ids": ["ufc_profile"]},
            {"id": "fact_4", "text": "Не проигрывает на протяжении семи лет — её победная серия длится с декабря 2019 года.", "source_ids": ["ufc_profile"]},
            {"id": "fact_5", "text": "В октябре 2026 года на UFC 332 перебила базовую кикбоксёршу Ван Цун со счётом 109–98 по значимым ударам.", "source_ids": ["ufc_profile"]},
            {"id": "fact_6", "text": "До дебюта в UFC более двух лет не могла драться из-за перелома руки и отмены турниров в пандемию.", "source_ids": ["ufc_profile"]}
        ]
    },
    "alexa_grasso": {
        "positioning": "Первая мексиканская чемпионка в истории UFC, сочетающая филигранный комбинационный бокс с опасным джиу-джитсу.",
        "career_story": [
            "Выросла в боксёрском зале Гвадалахары, дебютировала в профи в 2012 году и после перехода в наилегчайший вес раскрыла свой пиковый потенциал.",
            "В 2026 году вернулась в титульную гонку двумя яркими победами — нокаутом в первом раунде над Мэйси Барбер и победой над Манон Фиоро на сентябрьском Noche UFC."
        ],
        "stats": {
            "record": {"wins": 18, "losses": 5, "draws": 1, "no_contests": 0},
            "wins_by": {"ko_tko": 5, "submission": 2, "decision": 11},
            "current_streak": {"type": "win", "count": 2},
            "promotion_rank": 2,
            "pound_for_pound_rank": 6,
            "verified_at": "2026-11-13",
            "source_ids": ["ufc_profile", "ufc_rankings"]
        },
        "facts": [
            {"id": "fact_1", "text": "Тренируется в зале Lobo Gym в Гвадалахаре под руководством собственного дяди Франсиско Грассо.", "source_ids": ["ufc_profile"]},
            {"id": "fact_2", "text": "До перехода в UFC выиграла все четыре своих поединка в женской лиге Invicta FC.", "source_ids": ["ufc_profile"]},
            {"id": "fact_3", "text": "В сентябре 2026 года отправила габаритную француженку Манон Фиоро в нокдаун и забрала победу единогласным решением.", "source_ids": ["ufc_profile"]},
            {"id": "fact_4", "text": "В марте 2023 года сотворила один из главных апсетов десятилетия, заставив сдаться Валентину Шевченко в четвёртом раунде.", "source_ids": ["ufc_profile"]},
            {"id": "fact_5", "text": "Была удостоена премии за сабмишен 2023 года по версиям World MMA Awards и ESPN.", "source_ids": ["ufc_profile"]},
            {"id": "fact_6", "text": "В марте 2026 года оформила свой первый нокаут за девять лет выступлений в UFC, финишировав Мэйси Барбер.", "source_ids": ["ufc_profile"]}
        ]
    },
    "manon_fiorot": {
        "stats": {
            "record": {"wins": 13, "losses": 3, "draws": 0, "no_contests": 0},
            "wins_by": {"ko_tko": 7, "submission": 0, "decision": 6},
            "current_streak": {"type": "loss", "count": 1},
            "promotion_rank": 4,
            "pound_for_pound_rank": 11,
            "verified_at": "2026-11-13",
            "source_ids": ["ufc_profile", "ufc_rankings"]
        }
    },
    "erin_blanchfield": {
        "stats": {
            "record": {"wins": 14, "losses": 3, "draws": 0, "no_contests": 0},
            "wins_by": {"ko_tko": 2, "submission": 5, "decision": 7},
            "current_streak": {"type": "loss", "count": 1},
            "promotion_rank": 5,
            "pound_for_pound_rank": 12,
            "verified_at": "2026-11-13",
            "source_ids": ["ufc_profile", "ufc_rankings"]
        }
    },
    "tatiana_suarez": {
        "career_story": [
            "После успешной борцовской юности победила рак щитовидной железы, выиграла 23-й сезон The Ultimate Fighter и ворвалась в элиту UFC.",
            "Преодолев многолетние травмы шеи и колена, в ноябре 2026 года уверенно перебила экс-претендентку Вирну Яндиробу (98–45 по общему числу ударов)."
        ],
        "stats": {
            "record": {"wins": 14, "losses": 1, "draws": 0, "no_contests": 0},
            "wins_by": {"ko_tko": 2, "submission": 7, "decision": 5},
            "current_streak": {"type": "win", "count": 3},
            "promotion_rank": 1,
            "pound_for_pound_rank": 8,
            "verified_at": "2026-11-13",
            "source_ids": ["ufc_profile", "ufc_rankings"]
        }
    }
}


# 3. 8 НОВЫХ ТОПОВЫХ И МЕДИЙНЫХ БОЙЦОВ (4 МУЖЧИНЫ + 4 ЖЕНЩИНЫ)
NEW_FIGHTERS = [
    {
        "schema_version": 1,
        "id": "shavkat_rakhmonov",
        "name_ru": "Шавкат Рахмонов",
        "name_en": "Shavkat Rakhmonov",
        "gender": "male",
        "country": "Казахстан",
        "promotion": "UFC",
        "weight_class": "полусредний вес",
        "positioning": "Непобеждённый казахстанский финишер, сочетающий хладнокровный прессинг в стойке с удушающим контролем в клинче и партере.",
        "career_story": [
            "Завоевал чемпионские пояса M-1 Global и KZMMAF, после чего в 2020 году дебютировал в UFC и выиграл первые шесть боёв в октагоне досрочно.",
            "В декабре 2024 года на UFC 310 нанёс первое поражение Иэну Гэрри в пятираундовом претендентском бою, доведя профессиональный рекорд до 19–0."
        ],
        "fighting_style": [
            "Длинные прямые удары, жёсткие колени в клинче и постоянное сокращение дистанции.",
            "Мгновенные переходы на гильотину и удушение сзади при любой ошибке соперника у сетки."
        ],
        "titles": {
            "current": [],
            "former": [],
            "other": [
                {
                    "organization": "M-1 Global",
                    "name_ru": "Чемпион M-1 Global в полусреднем весе",
                    "division": "полусредний вес",
                    "source_ids": ["ufc_profile"]
                }
            ]
        },
        "achievements": [
            "Идеальный рекорд 19–0 в профессиональном MMA.",
            "18 из 19 побед одержал досрочно (8 нокаутами, 10 сабмишенами).",
            "Первый представитель Казахстана в топ-3 рейтинга UFC."
        ],
        "distinctive_features": [
            "Выходит в октагон в традиционном казахском головном уборе тымаке.",
            "Обладает почти стопроцентным показателем финишей."
        ],
        "stats": {
            "record": {"wins": 19, "losses": 0, "draws": 0, "no_contests": 0},
            "wins_by": {"ko_tko": 8, "submission": 10, "decision": 1},
            "current_streak": {"type": "win", "count": 19},
            "promotion_rank": 2,
            "pound_for_pound_rank": 11,
            "verified_at": "2026-11-13",
            "source_ids": ["ufc_profile", "ufc_rankings"]
        },
        "facts": [
            {"id": "fact_1", "text": "В восемнадцать лет стал самым молодым чемпионом мира в истории любительского союза WMMAA.", "source_ids": ["ufc_profile"]},
            {"id": "fact_2", "text": "Первые восемнадцать боёв в профессиональной карьере завершил досрочно — ни один соперник не дотянул до финального гонга до декабря 2024 года.", "source_ids": ["ufc_profile"]},
            {"id": "fact_3", "text": "До подписания контракта с мировыми промоушенами подрабатывал грузчиком на рынке в Караганде.", "source_ids": ["ufc_profile"]},
            {"id": "fact_4", "text": "Его родная младшая сестра Сора Рахмонова также профессионально выступала в смешанных единоборствах.", "source_ids": ["ufc_profile"]},
            {"id": "fact_5", "text": "Задушил Стивена «Вандербоя» Томпсона наUFC 296, став первым бойцом в истории, кто финишировал его приёмом.", "source_ids": ["ufc_profile"]},
            {"id": "fact_6", "text": "Готовится к главным поединкам в американском зале Kill Cliff FC во Флориде под руководством Генри Хуфта.", "source_ids": ["ufc_profile"]}
        ],
        "angles": [
            {"id": "angle_1", "title": "Инстинкт финишера", "focus": "Почему почти все его бои заканчиваются до решения судей.", "fact_ids": ["fact_2", "fact_5"]},
            {"id": "angle_2", "title": "Путь кочевника", "focus": "От рынка в Караганде и титула M-1 до элиты UFC.", "fact_ids": ["fact_1", "fact_3"]},
            {"id": "angle_3", "title": "Семья единоборцев", "focus": "Спортивная династия и подготовка в Kill Cliff.", "fact_ids": ["fact_4", "fact_6"]}
        ],
        "sources": [
            {"id": "ufc_profile", "title": "Shavkat Rakhmonov — UFC athlete profile", "url": "https://www.ufc.com/athlete/shavkat-rakhmonov", "checked_at": "2026-11-13"},
            {"id": "ufc_rankings", "title": "UFC Rankings", "url": "https://www.ufc.com/rankings", "checked_at": "2026-11-13"}
        ],
        "image": {
            "local_path": "project/content/fighters/shavkat_rakhmonov/photo.jpg",
            "source_page": "https://commons.wikimedia.org/wiki/File:Rahkmonov_2.png",
            "creator": "Wikimedia Commons / CC BY 3.0",
            "license": "CC BY 3.0",
            "rights_status": "cleared_with_embedded_attribution",
            "publication_ready": True
        },
        "last_posted_at": None,
        "enabled": True
    },
    {
        "schema_version": 1,
        "id": "amanda_nunes",
        "name_ru": "Аманда Нуньес",
        "name_en": "Amanda Nunes",
        "gender": "female",
        "country": "Бразилия",
        "promotion": "UFC",
        "weight_class": "женский легчайший вес",
        "positioning": "Величайшая женщина-боец в истории MMA и бывшая двойная чемпионка UFC, вернувшаяся в октагон ради супербоя против Кайлы Харрисон.",
        "career_story": [
            "Дебютировала в профи в 2008 году, прошла Strikeforce и Invicta FC, а в UFC одновременно удерживала и защищала пояса в легчайшем и полулёгком дивизионах.",
            "Ушла непобеждённой чемпионкой летом 2023 года, была введена в Зал славы UFC, но в 2026 году возобновила карьеру ради противостояния с Кайлой Харрисон."
        ],
        "fighting_style": [
            "Разрушительный правый кросс, жёсткие лоу-кики и нокаутирующая мощь с первых секунд.",
            "Чёрный пояс по BJJ и коричневый по дзюдо, позволяющие уверенно контролировать партер."
        ],
        "titles": {
            "current": [],
            "former": [
                {
                    "organization": "UFC",
                    "name_ru": "Двукратная чемпионка UFC в легчайшем весе",
                    "division": "женский легчайший вес",
                    "won_at": "2016-07 / 2022-07",
                    "defenses": 6,
                    "source_ids": ["ufc_profile"]
                },
                {
                    "organization": "UFC",
                    "name_ru": "Чемпионка UFC в полулёгком весе",
                    "division": "женский полулёгкий вес",
                    "won_at": "2018-12",
                    "defenses": 2,
                    "source_ids": ["ufc_profile"]
                }
            ],
            "other": []
        },
        "achievements": [
            "Первая женщина в истории UFC, владевшая двумя поясами одновременно и защищавшая оба титула.",
            "Одиннадцать побед в титульных боях UFC (абсолютный рекорд среди женщин).",
            "Член современного крыла Зала славы UFC."
        ],
        "distinctive_features": [
            "Победила абсолютно всех бывших чемпионок UFC в легчайшем и полулёгком весах своего поколения.",
            "Обладает сильнейшим одиночным ударом в истории женских дивизионов."
        ],
        "stats": {
            "record": {"wins": 23, "losses": 5, "draws": 0, "no_contests": 0},
            "wins_by": {"ko_tko": 13, "submission": 4, "decision": 6},
            "current_streak": {"type": "win", "count": 2},
            "promotion_rank": 1,
            "pound_for_pound_rank": 2,
            "verified_at": "2026-11-13",
            "source_ids": ["ufc_profile", "ufc_rankings"]
        },
        "facts": [
            {"id": "fact_1", "text": "В декабре 2018 года нокаутировала непобеждённую на протяжении 13 лет Крис Сайборг всего за 51 секунду.", "source_ids": ["ufc_profile"]},
            {"id": "fact_2", "text": "Оформила самый быстрый нокаут в истории женских титульных боёв легчайшего веса, отправив Холли Холм в нокаут хай-киком в первом раунде, а Ронду Роузи — за 48 секунд.", "source_ids": ["ufc_profile"]},
            {"id": "fact_3", "text": "В её послужном списке победы над шестью разными чемпионками UFC: Тейт, Роузи, Шевченко, Сайборг, Холм и де Рандами.", "source_ids": ["ufc_profile"]},
            {"id": "fact_4", "text": "До переезда в США жила прямо в помещении спортзала в Салвадоре (штат Баия), так как не имела денег на аренду жилья.", "source_ids": ["ufc_profile"]},
            {"id": "fact_5", "text": "Их принципиальное соперничество с Кайлой Харрисон началось ещё со времён совместных тренировок в зале American Top Team.", "source_ids": ["ufc_profile"]}
        ],
        "angles": [
            {"id": "angle_1", "title": "Охотница за легендами", "focus": "Как Нуньес зачистила два дивизиона от всех экс-чемпионок.", "fact_ids": ["fact_1", "fact_3"]},
            {"id": "angle_2", "title": "Нокаут за секунды", "focus": "Феномен стартовой мощи Львицы в титульных боях.", "fact_ids": ["fact_2"]},
            {"id": "angle_3", "title": "Большое возвращение", "focus": "История бывших одноклубниц по ATT — Нуньес и Харрисон.", "fact_ids": ["fact_4", "fact_5"]}
        ],
        "sources": [
            {"id": "ufc_profile", "title": "Amanda Nunes — UFC athlete profile", "url": "https://www.ufc.com/athlete/amanda-nunes", "checked_at": "2026-11-13"},
            {"id": "ufc_rankings", "title": "UFC Rankings", "url": "https://www.ufc.com/rankings", "checked_at": "2026-11-13"}
        ],
        "image": {
            "local_path": "project/content/fighters/amanda_nunes/photo.jpg",
            "source_page": "https://commons.wikimedia.org/wiki/File:Ceremonial_weigh_ins_-_Amanda_Nunes_vs_Julianna_Pe%C3%B1a_UFC_269_(cropped).jpg",
            "creator": "Jgui / Wikimedia Commons",
            "license": "CC BY 3.0",
            "rights_status": "cleared_with_embedded_attribution",
            "publication_ready": True
        },
        "last_posted_at": None,
        "enabled": True
    },
    {
        "schema_version": 1,
        "id": "magomed_ankalaev",
        "name_ru": "Магомед Анкалаев",
        "name_en": "Magomed Ankalaev",
        "gender": "male",
        "country": "Россия",
        "promotion": "UFC",
        "weight_class": "полутяжёлый вес",
        "positioning": "Экс-чемпион UFC в полутяжёлом весе: расчётливый контрпанчер-левша с фундаментальной базой боевого самбо и непробиваемой защитой от борьбы.",
        "career_story": [
            "После доминирования в любительском ММА и завоевания пояса WFCA пришёл в UFC в 2018 году, выдав серию из 13 боёв без поражений.",
            "Владел чемпионским поясом UFC в полутяжёлом весе, а в июле 2026 года на турнире в Абу-Даби нокаутировал Богдана Гуськова в первом раунде."
        ],
        "fighting_style": [
            "Выверенная работа вторым номером из стойки левши, быстрые встречные серии и хай-кики.",
            "Силовой клинч, контроль в партере и 87% успешной защиты от тейкдаунов."
        ],
        "titles": {
            "current": [],
            "former": [
                {
                    "organization": "UFC",
                    "name_ru": "Чемпион UFC в полутяжёлом весе",
                    "division": "полутяжёлый вес",
                    "won_at": "2025-03",
                    "defenses": 0,
                    "source_ids": ["ufc_profile"]
                }
            ],
            "other": [
                {
                    "organization": "WFCA",
                    "name_ru": "Чемпион WFCA в полутяжёлом весе",
                    "division": "полутяжёлый вес",
                    "source_ids": ["ufc_profile"]
                }
            ]
        },
        "achievements": [
            "Бывший чемпион UFC в полутяжёлом весе.",
            "Вторая по продолжительности серия без поражений в истории полутяжёлого веса UFC (13 боёв подряд после Джона Джонса).",
            "Заслуженный мастер спорта России по ММА."
        ],
        "distinctive_features": [
            "Один из самых дисциплинированных тактиков полутяжёлого дивизиона.",
            "Крайне редко пропускает чистые силовые удары на дистанции."
        ],
        "stats": {
            "record": {"wins": 22, "losses": 2, "draws": 1, "no_contests": 1},
            "wins_by": {"ko_tko": 12, "submission": 0, "decision": 10},
            "current_streak": {"type": "win", "count": 1},
            "promotion_rank": 1,
            "pound_for_pound_rank": 10,
            "verified_at": "2026-11-13",
            "source_ids": ["ufc_profile", "ufc_rankings"]
        },
        "facts": [
            {"id": "fact_1", "text": "Его дебютный бой в UFC против Пола Крейга в 2018 году завершился сдачей ровно за одну секунду до конца третьего раунда, который Анкалаев уверенно выигрывал.", "source_ids": ["ufc_profile"]},
            {"id": "fact_2", "text": "До перехода в профессионалы выиграл чемпионат мира и четыре чемпионата России по союзу ММА.", "source_ids": ["ufc_profile"]},
            {"id": "fact_3", "text": "В студенческие годы в Махачкале начинал с греко-римской борьбы и только затем переключился на боевое самбо.", "source_ids": ["ufc_profile"]},
            {"id": "fact_4", "text": "В июле 2026 года закрыл реванш с Перейрой ярким нокаутом над Богданом Гуськовым за 2 минуты и 41 секунду.", "source_ids": ["ufc_profile"]},
            {"id": "fact_5", "text": "Ни одна из его двадцати двух побед в профи не была одержана приёмом — все финиши оформлены исключительно нокаутами и ТКО.", "source_ids": ["ufc_profile"]}
        ],
        "angles": [
            {"id": "angle_1", "title": "Снайпер в полутяжах", "focus": "Почему базовый самбист финиширует соперников только ударами.", "fact_ids": ["fact_3", "fact_5"]},
            {"id": "angle_2", "title": "Урок последней секунды", "focus": "Как обидное поражение в дебюте запустило серию из 13 боёв без осечек.", "fact_ids": ["fact_1", "fact_2"]},
            {"id": "angle_3", "title": "Возвращение в Абу-Даби", "focus": "Досрочная победа летом 2026 года и новая погоня за поясом.", "fact_ids": ["fact_4"]}
        ],
        "sources": [
            {"id": "ufc_profile", "title": "Magomed Ankalaev — UFC athlete profile", "url": "https://www.ufc.com/athlete/magomed-ankalaev", "checked_at": "2026-11-13"},
            {"id": "ufc_rankings", "title": "UFC Rankings", "url": "https://www.ufc.com/rankings", "checked_at": "2026-11-13"}
        ],
        "image": {
            "local_path": "project/content/fighters/magomed_ankalaev/photo.jpg",
            "source_page": "https://commons.wikimedia.org/wiki/File:Magomed_Ankalaev_at_UFC_Fight_Night_136_in_Moscow,_Russia.jpg",
            "creator": "MMAnytt",
            "license": "CC BY 3.0",
            "rights_status": "cleared_with_embedded_attribution",
            "publication_ready": True
        },
        "last_posted_at": None,
        "enabled": True
    },
    {
        "schema_version": 1,
        "id": "jasmine_jasudavicius",
        "name_ru": "Жасмин Ясудавичюс",
        "name_en": "Jasmine Jasudavicius",
        "gender": "female",
        "country": "Канада",
        "promotion": "UFC",
        "weight_class": "женский наилегчайший вес",
        "positioning": "Главная канадская претендентка женского наилегчайшего веса, пробившаяся в топ-3 за счёт вязкого грэпплинга, габаритов и relentless-контроля.",
        "career_story": [
            "Пришла в единоборства только в 26 лет, получила контракт через Dana White's Contender Series в 2021 году и закрепилась в элите дивизиона.",
            "Выиграла семь из восьми боёв в UFC в 2024–2026 годах, включая досрочную победу над экс-чемпионкой Джессикой Андраде и триумф над Эрин Бланчфилд в октябре 2026-го."
        ],
        "fighting_style": [
            "Силовые переводы от сетки, контроль со спины с заправленным треугольником на корпусе и жёсткий граунд-энд-паунд.",
            "Использование преимущества в росте (170 см) и размахе рук для сближения в клинч."
        ],
        "titles": {"current": [], "former": [], "other": []},
        "achievements": [
            "Победы над экс-чемпионкой UFC Джессикой Андраде и топ-грэпплершей Эрин Бланчфилд.",
            "Рекорд UFC по разнице ударов в трёхраундовом бою женского наилегчайшего веса (+290 ударов против Присцилы Кашуэйры).",
            "Три бонуса «Выступление вечера» подряд в 2024–2025 годах."
        ],
        "distinctive_features": [
            "Начала тренироваться без какой-либо детской спортивной базы уже во взрослом возрасте.",
            "Умеет перебарывать даже профильных мастеров бразильского джиу-джитсу."
        ],
        "stats": {
            "record": {"wins": 16, "losses": 4, "draws": 0, "no_contests": 0},
            "wins_by": {"ko_tko": 2, "submission": 4, "decision": 10},
            "current_streak": {"type": "win", "count": 2},
            "promotion_rank": 3,
            "pound_for_pound_rank": 10,
            "verified_at": "2026-11-13",
            "source_ids": ["ufc_profile", "ufc_rankings"]
        },
        "facts": [
            {"id": "fact_1", "text": "Впервые переступила порог бойцовского зала в 2016 году в возрасте 26 лет после случайного знакомства с тренером Крисом Прикеттом.", "source_ids": ["ufc_profile"]},
            {"id": "fact_2", "text": "На турнире UFC 297 в Торонто нанесла сопернице 326 ударов за неполные три раунда, пропустив в ответ всего 36.", "source_ids": ["ufc_profile"]},
            {"id": "fact_3", "text": "В мае 2025 года в Монреале задушила экс-чемпионку UFC Джессику Андраде уже в первом раунде.", "source_ids": ["ufc_profile"]},
            {"id": "fact_4", "text": "В октябре 2026 года в Эдмонтоне провела пять успешных тейкдаунов против базовой чемпионки EBI Эрин Бланчфилд.", "source_ids": ["ufc_profile"]},
            {"id": "fact_5", "text": "Имеет литовские корни по отцовской линии и представляет зал Niagara Top Team в Онтарио.", "source_ids": ["ufc_profile"]}
        ],
        "angles": [
            {"id": "angle_1", "title": "Старт в 26 лет", "focus": "Как без детского спорта дойти до топ-3 UFC.", "fact_ids": ["fact_1", "fact_5"]},
            {"id": "angle_2", "title": "Рекордный разгром", "focus": "Абсолютный рекорд дивизиона по доминированию в партере.", "fact_ids": ["fact_2"]},
            {"id": "angle_3", "title": "Гроза фавориток", "focus": "Победы над Андраде и Бланчфилд на канадских аренах.", "fact_ids": ["fact_3", "fact_4"]}
        ],
        "sources": [
            {"id": "ufc_profile", "title": "Jasmine Jasudavicius — UFC athlete profile", "url": "https://www.ufc.com/athlete/jasmine-jasudavicius", "checked_at": "2026-11-13"},
            {"id": "ufc_rankings", "title": "UFC Rankings", "url": "https://www.ufc.com/rankings", "checked_at": "2026-11-13"}
        ],
        "image": {
            "local_path": "project/content/fighters/jasmine_jasudavicius/photo.jpg",
            "source_page": "https://commons.wikimedia.org/wiki/File:Jasmine_Jasudavicius_2023.png",
            "creator": "MM-eh",
            "license": "CC BY 3.0",
            "rights_status": "cleared_with_embedded_attribution",
            "publication_ready": True
        },
        "last_posted_at": None,
        "enabled": True
    },
    {
        "schema_version": 1,
        "id": "ciryl_gane",
        "name_ru": "Сирил Ган",
        "name_en": "Ciryl Gane",
        "gender": "male",
        "country": "Франция",
        "promotion": "UFC",
        "weight_class": "тяжёлый вес",
        "positioning": "Двукратный временный чемпион UFC в тяжёлом весе: французский тяжеловес с работой ног легковеса и безупречной базой тайского бокса.",
        "career_story": [
            "После непобеждённой карьеры в профессиональном муай-тай (13–0) дебютировал в MMA в 2018 году и уже через три года взял временный пояс UFC.",
            "В июне 2026 года на историческом турнире UFC Freedom 250 в Вашингтоне финишировал Алекса Перейру во втором раунде, повторно завоевав временный титул чемпиона в тяжёлом весе."
        ],
        "fighting_style": [
            "Челночное движение на ногах, постоянная смена стоек и точные удары по всем этажам с дальней дистанции.",
            "Хладнокровная защита в стойке (61% отражённых ударов) и работа коленями и локтями в тайском клинче."
        ],
        "titles": {
            "current": [
                {
                    "organization": "UFC",
                    "name_ru": "Временный чемпион UFC в тяжёлом весе",
                    "division": "тяжёлый вес",
                    "won_at": "2026-06",
                    "defenses": 0,
                    "source_ids": ["ufc_profile"]
                }
            ],
            "former": [
                {
                    "organization": "UFC",
                    "name_ru": "Временный чемпион UFC в тяжёлом весе",
                    "division": "тяжёлый вес",
                    "won_at": "2021-08",
                    "defenses": 0,
                    "source_ids": ["ufc_profile"]
                }
            ],
            "other": [
                {
                    "organization": "AFMT",
                    "name_ru": "Двукратный чемпион Франции по муай-тай",
                    "division": "тяжёлый вес",
                    "source_ids": ["ufc_profile"]
                }
            ]
        },
        "achievements": [
            "Двукратный обладатель временного титула UFC в тяжёлом весе (2021, 2026).",
            "Технический нокаут над экс-чемпионом двух дивизионов Алексом Перейрой на турнире UFC Freedom 250.",
            "Непобеждённый рекорд 13–0 в профессиональном тайском боксе."
        ],
        "distinctive_features": [
            "При весе 112 кг двигается на челноке все пять раундов.",
            "Одерживал победы в UFC как нокаутами, так и болевыми приёмами (включая скручивание пятки)."
        ],
        "stats": {
            "record": {"wins": 14, "losses": 2, "draws": 0, "no_contests": 1},
            "wins_by": {"ko_tko": 7, "submission": 3, "decision": 4},
            "current_streak": {"type": "win", "count": 2},
            "promotion_rank": 1,
            "pound_for_pound_rank": 13,
            "verified_at": "2026-11-13",
            "source_ids": ["ufc_profile", "ufc_rankings"]
        },
        "facts": [
            {"id": "fact_1", "text": "В первом же году в UFC оформил редчайший для тяжеловесов сабмишен — скручивание пятки (heel hook) на последней минуте боя против Дон'Тейла Мэйса.", "source_ids": ["ufc_profile"]},
            {"id": "fact_2", "text": "В июне 2026 года за досрочную победу над Алексом Перейрой на лужайке у Белого дома получил специальный бонус в размере 425 000 долларов.", "source_ids": ["ufc_profile"]},
            {"id": "fact_3", "text": "До знакомства с единоборствами в 24 года играл в баскетбол и работал продавцом-консультантом в мебельном салоне в Париже.", "source_ids": ["ufc_profile"]},
            {"id": "fact_4", "text": "Прозвище Bon Gamin переводится с французского как «Хороший парень» и отражает его спокойный характер за пределами клетки.", "source_ids": ["ufc_profile"]},
            {"id": "fact_5", "text": "Снялся в нескольких художественных фильмах и проектах Netflix, включая криминальную драму «КО» (Bastion 36).", "source_ids": ["ufc_profile"]}
        ],
        "angles": [
            {"id": "angle_1", "title": "Триумф над Поатаном", "focus": "Как Ган остановил поход Алекса Перейры за третьим поясом.", "fact_ids": ["fact_2"]},
            {"id": "angle_2", "title": "Феномен лёгких ног", "focus": "Путь из мебельного магазина и муай-тай в элиту UFC.", "fact_ids": ["fact_1", "fact_3"]},
            {"id": "angle_3", "title": "Хороший парень из Парижа", "focus": "Медийность, кино и характер чемпиона.", "fact_ids": ["fact_4", "fact_5"]}
        ],
        "sources": [
            {"id": "ufc_profile", "title": "Ciryl Gane — UFC athlete profile", "url": "https://www.ufc.com/athlete/ciryl-gane", "checked_at": "2026-11-13"},
            {"id": "ufc_rankings", "title": "UFC Rankings", "url": "https://www.ufc.com/rankings", "checked_at": "2026-11-13"}
        ],
        "image": {
            "local_path": "project/content/fighters/ciryl_gane/photo.jpg",
            "source_page": "https://commons.wikimedia.org/wiki/File:UFC_Freedom_250_Ceremonial_Weigh_In_(9748626)(cropped).jpg",
            "creator": "Sgt. 1st Class Brittany Primavera / U.S. Army",
            "license": "Public Domain — U.S. Army work",
            "rights_status": "cleared_no_public_credit",
            "publication_ready": True
        },
        "last_posted_at": None,
        "enabled": True
    },
    {
        "schema_version": 1,
        "id": "julianna_pena",
        "name_ru": "Джулианна Пенья",
        "name_en": "Julianna Pena",
        "gender": "female",
        "country": "США",
        "promotion": "UFC",
        "weight_class": "женский легчайший вес",
        "positioning": "Двукратная чемпионка UFC в женском легчайшем весе и первая женщина-победительница шоу The Ultimate Fighter, известная неуступчивым характером.",
        "career_story": [
            "Начала карьеру в 2009 году, выиграла исторический 18-й сезон TUF и преодолела двухлетний простой после тяжёлой травмы колена и рождения дочери.",
            "В декабре 2021 года сотворила одну из главных сенсаций в истории UFC, задушив Аманду Нуньес, а в октябре 2024-го вернула чемпионский пояс в бою с Ракель Пеннингтон."
        ],
        "fighting_style": [
            "Силовой прессинг, затяжной клинч у сетки и изматывающий граунд-энд-паунд.",
            "Цепкие удушающие приёмы (гильотина и удушение сзади) во второй половине боя."
        ],
        "titles": {
            "current": [],
            "former": [
                {
                    "organization": "UFC",
                    "name_ru": "Двукратная чемпионка UFC в легчайшем весе",
                    "division": "женский легчайший вес",
                    "won_at": "2021-12 / 2024-10",
                    "defenses": 0,
                    "source_ids": ["ufc_profile"]
                }
            ],
            "other": [
                {
                    "organization": "UFC",
                    "name_ru": "Победительница The Ultimate Fighter 18",
                    "division": "женский легчайший вес",
                    "source_ids": ["ufc_profile"]
                }
            ]
        },
        "achievements": [
            "Двукратная чемпионка UFC в легчайшем весе.",
            "Первая женщина в истории, выигравшая турнир The Ultimate Fighter (2013).",
            "Автор одного из крупнейших апсетов в истории смешанных единоборств (UFC 269)."
        ],
        "distinctive_features": [
            "Никогда не отступает в разменах и навязывает вязкую рубку на ближней дистанции.",
            "Прозвище The Venezuelan Vixen подчёркивает её венесуэльские и мексиканские корни."
        ],
        "stats": {
            "record": {"wins": 13, "losses": 6, "draws": 0, "no_contests": 0},
            "wins_by": {"ko_tko": 3, "submission": 5, "decision": 5},
            "current_streak": {"type": "loss", "count": 1},
            "promotion_rank": 5,
            "pound_for_pound_rank": 10,
            "verified_at": "2026-11-13",
            "source_ids": ["ufc_profile", "ufc_rankings"]
        },
        "facts": [
            {"id": "fact_1", "text": "В 2014 году получила разрыв всех связок колена на тренировке и пропустила hampir два года, но вернулась с тремя победами подряд.", "source_ids": ["ufc_profile"]},
            {"id": "fact_2", "text": "Перед боем на UFC 269 коэффициенты против неё доходили до 8 к 1, однако она заставила Аманду Нуньес сдаться во втором раунде.", "source_ids": ["ufc_profile"]},
            {"id": "fact_3", "text": "Помимо выступлений в клетке работает англоязычным комментатором на турнирах по ММА и вольной борьбе.", "source_ids": ["ufc_profile"]},
            {"id": "fact_4", "text": "Пришла в зал Sikjitsu в Спокане в 19 лет изначально просто для того, чтобы сбросить вес с помощью кардио-кикбоксинга.", "source_ids": ["ufc_profile"]},
            {"id": "fact_5", "text": "Делит первое место в истории женского легчайшего веса UFC по количеству побед сабмишенами.", "source_ids": ["ufc_profile"]}
        ],
        "angles": [
            {"id": "angle_1", "title": "Апсет века", "focus": "Как Пенья сделала то, во что не верил никто перед UFC 269.", "fact_ids": ["fact_2"]},
            {"id": "angle_2", "title": "Пионер TUF", "focus": "Путь от кардио-кикбоксинга до двух чемпионских поясов UFC.", "fact_ids": ["fact_1", "fact_4"]},
            {"id": "angle_3", "title": "Голос у микрофона", "focus": "Работа комментатором и рекорды в партере.", "fact_ids": ["fact_3", "fact_5"]}
        ],
        "sources": [
            {"id": "ufc_profile", "title": "Julianna Pena — UFC athlete profile", "url": "https://www.ufc.com/athlete/julianna-pena", "checked_at": "2026-11-13"},
            {"id": "ufc_rankings", "title": "UFC Rankings", "url": "https://www.ufc.com/rankings", "checked_at": "2026-11-13"}
        ],
        "image": {
            "local_path": "project/content/fighters/julianna_pena/photo.jpg",
            "source_page": "https://commons.wikimedia.org/wiki/File:2nd_MLG_company_commander_helps_America%E2%80%99s_heroes_140116-M-XX123-001_(cropped).jpg",
            "creator": "U.S. Marine Corps",
            "license": "Public Domain — U.S. Marine Corps work",
            "rights_status": "cleared_no_public_credit",
            "publication_ready": True
        },
        "last_posted_at": None,
        "enabled": True
    },
    {
        "schema_version": 1,
        "id": "joshua_van",
        "name_ru": "Джошуа Ван",
        "name_en": "Joshua Van",
        "gender": "male",
        "country": "США / Мьянма",
        "promotion": "UFC",
        "weight_class": "наилегчайший вес",
        "positioning": "Действующий чемпион UFC в наилегчайшем весе и первый чемпион организации, родившийся в 2000-х годах, обладающий рекордным темпом ударов.",
        "career_story": [
            "Переехал с семьёй из Мьянмы в Хьюстон в детстве, дебютировал в профи в 2021 году, взял пояс Fury FC и ворвался в UFC в 21 год.",
            "В декабре 2025 года завоевал титул UFC против Алешандре Пантожи, а в 2026-м провёл две яркие защиты — нокаутировав Тацуро Таиру в пятом раунде на UFC 328 и повторно победив Пантожу на UFC 331."
        ],
        "fighting_style": [
            "Ураганный бокс на средней дистанции с рекордной плотностью более 8 значимых попаданий в минуту.",
            "Жёсткие серии по корпусу, быстрые оттягивания и 75% защиты от тейкдаунов."
        ],
        "titles": {
            "current": [
                {
                    "organization": "UFC",
                    "name_ru": "Чемпион UFC в наилегчайшем весе",
                    "division": "наилегчайший вес",
                    "won_at": "2025-12",
                    "defenses": 2,
                    "source_ids": ["ufc_profile"]
                }
            ],
            "former": [],
            "other": [
                {
                    "organization": "Fury FC",
                    "name_ru": "Чемпион Fury FC в наилегчайшем весе",
                    "division": "наилегчайший вес",
                    "source_ids": ["ufc_profile"]
                }
            ]
        },
        "achievements": [
            "Первый чемпион в истории UFC, родившийся в 2000-х годах, и первый чемпион родом из Мьянмы.",
            "Второй самый молодой чемпион в истории UFC после Джона Джонса (завоевал пояс в 24 года и 57 дней).",
            "Абсолютный рекорд UFC по количеству значимых ударов в минуту (8,43)."
        ],
        "distinctive_features": [
            "Наращивает объём ударов от раунда к раунду, ломая темп соперников.",
            "Три боя подряд в 2025–2026 годах получали бонус «Лучший бой вечера»."
        ],
        "stats": {
            "record": {"wins": 18, "losses": 2, "draws": 0, "no_contests": 0},
            "wins_by": {"ko_tko": 9, "submission": 2, "decision": 7},
            "current_streak": {"type": "win", "count": 8},
            "promotion_rank": None,
            "pound_for_pound_rank": 5,
            "verified_at": "2026-11-13",
            "source_ids": ["ufc_profile", "ufc_rankings"]
        },
        "facts": [
            {"id": "fact_1", "text": "В первом титульном бою на UFC 323 оформил самый быстрый финиш в истории титульных боёв наилегчайшего веса — за 26 секунд.", "source_ids": ["ufc_profile"]},
            {"id": "fact_2", "text": "В реванше против Алешандре Пантожи в сентябре 2026 года донёс до цели 181 значимый удар (при 259 точных ударах всего).", "source_ids": ["ufc_profile"]},
            {"id": "fact_3", "text": "В июне 2025 года принял претендентский бой против Брэндона Ройвала на коротком уведомлении всего через три недели после предыдущего нокаута.", "source_ids": ["ufc_profile"]},
            {"id": "fact_4", "text": "Начал тренироваться в зале 4oz Fight Club в Хьюстоне лишь в 19 лет — за год до профессионального дебюта.", "source_ids": ["ufc_profile"]},
            {"id": "fact_5", "text": "В мае 2026 года нанёс первое поражение в карьере японскому проспекту Тацуро Таире, нокаутировав его в пятом раунде.", "source_ids": ["ufc_profile"]}
        ],
        "angles": [
            {"id": "angle_1", "title": "Поколение 2000-х", "focus": "Стремительный взлёт от новичка в 19 лет до чемпиона UFC в 24 года.", "fact_ids": ["fact_1", "fact_4"]},
            {"id": "angle_2", "title": "Пулемётный темп", "focus": "Рекордная статистика ударов и бонусы за лучшие бои вечера.", "fact_ids": ["fact_2", "fact_3"]},
            {"id": "angle_3", "title": "Две защиты в 2026-м", "focus": "Как Ван закрепил статус короля 125 фунтов.", "fact_ids": ["fact_5"]}
        ],
        "sources": [
            {"id": "ufc_profile", "title": "Joshua Van — UFC athlete profile", "url": "https://www.ufc.com/athlete/joshua-van", "checked_at": "2026-11-13"},
            {"id": "ufc_rankings", "title": "UFC Rankings", "url": "https://www.ufc.com/rankings", "checked_at": "2026-11-13"}
        ],
        "image": {
            "local_path": "project/content/fighters/joshua_van/photo.jpg",
            "source_page": "https://commons.wikimedia.org/wiki/File:Joshua_Van_1.png",
            "creator": "YouTube CC-BY / Wikimedia Commons",
            "license": "CC BY 3.0",
            "rights_status": "cleared_with_embedded_attribution",
            "publication_ready": True
        },
        "last_posted_at": None,
        "enabled": True
    },
    {
        "schema_version": 1,
        "id": "raquel_pennington",
        "name_ru": "Ракель Пеннингтон",
        "name_en": "Raquel Pennington",
        "gender": "female",
        "country": "США",
        "promotion": "UFC",
        "weight_class": "женский легчайший вес",
        "positioning": "Экс-чемпионка UFC в легчайшем весе и рекордсменка дивизиона по количеству проведённых боёв, прошедшая одиннадцатилетний путь к золоту.",
        "career_story": [
            "Попала в UFC в 2013 году через 18-й сезон The Ultimate Fighter и провела более двадцати поединков против сильнейших соперниц двух категорий.",
            "В январе 2024 года на UFC 297 победила Майру Буэно Силву и завоевала долгожданный пояс чемпионки UFC со второй титульной попытки."
        ],
        "fighting_style": [
            "Вязкий силовой бокс на ближней дистанции, жёсткий джеб и длительный контроль в клинче у сетки.",
            "Выносливость на пять раундов и опасные удушения гильотиной и бульдогом."
        ],
        "titles": {
            "current": [],
            "former": [
                {
                    "organization": "UFC",
                    "name_ru": "Чемпионка UFC в легчайшем весе",
                    "division": "женский легчайший вес",
                    "won_at": "2024-01",
                    "defenses": 0,
                    "source_ids": ["ufc_profile"]
                }
            ],
            "other": []
        },
        "achievements": [
            "Бывшая чемпионка UFC в женском легчайшем весе.",
            "Рекордсменка женского легчайшего дивизиона UFC по количеству боёв и времени в октагоне.",
            "Оформила редчайшее удушение «бульдог» (bulldog choke) в истории UFC."
        ],
        "distinctive_features": [
            "Олицетворяет стойкость и спортивное долголетие в женском ММА.",
            "Умеет затягивать более быстрых соперниц в силовой клинч."
        ],
        "stats": {
            "record": {"wins": 16, "losses": 10, "draws": 0, "no_contests": 0},
            "wins_by": {"ko_tko": 1, "submission": 4, "decision": 11},
            "current_streak": {"type": "loss", "count": 1},
            "promotion_rank": 4,
            "pound_for_pound_rank": 13,
            "verified_at": "2026-11-13",
            "source_ids": ["ufc_profile", "ufc_rankings"]
        },
        "facts": [
            {"id": "fact_1", "text": "В детстве и юности активно занималась хоккеем, баскетболом и софтболом, но сломала спину во время сноубординга и переключилась на бокс.", "source_ids": ["ufc_profile"]},
            {"id": "fact_2", "text": "На UFC 181 заставила Эшли Эванс-Смит потерять сознание приёмом «бульдог» ровно на последней секунде первого раунда (4:59).", "source_ids": ["ufc_profile"]},
            {"id": "fact_3", "text": "Завоевала чемпионский пояс UFC спустя 10 лет и 2 месяца после своего дебюта в организации.", "source_ids": ["ufc_profile"]},
            {"id": "fact_4", "text": "На UFC 205 в Нью-Йорке победила свою бывшую наставницу по шоу TUF Мишу Тейт, отправив ту в первую отставку.", "source_ids": ["ufc_profile"]},
            {"id": "fact_5", "text": "Жената на бывшей претендентке минимального веса UFC Тесии Пенелопе (Торрес).", "source_ids": ["ufc_profile"]}
        ],
        "angles": [
            {"id": "angle_1", "title": "Десять лет до золота", "focus": "Уникальная история терпения и пути к поясу UFC 297.", "fact_ids": ["fact_3", "fact_4"]},
            {"id": "angle_2", "title": "Королева клинча", "focus": "Редкий сабмишен на 4:59 и физическая выносливость.", "fact_ids": ["fact_1", "fact_2"]},
            {"id": "angle_3", "title": "Семейный дуэт в UFC", "focus": "Жизнь и тренировки двух ветеранов октагона.", "fact_ids": ["fact_5"]}
        ],
        "sources": [
            {"id": "ufc_profile", "title": "Raquel Pennington — UFC athlete profile", "url": "https://www.ufc.com/athlete/raquel-pennington", "checked_at": "2026-11-13"},
            {"id": "ufc_rankings", "title": "UFC Rankings", "url": "https://www.ufc.com/rankings", "checked_at": "2026-11-13"}
        ],
        "image": {
            "local_path": "project/content/fighters/raquel_pennington/photo.jpg",
            "source_page": "https://commons.wikimedia.org/wiki/File:Raquel_Pennington_MCCS_Twentynine_Palms_presents_an_action-packed_MMA_Fight_Night_Live_at_The_Combat_Center_(5).jpg",
            "creator": "Lance Cpl. Enge You / U.S. Marine Corps",
            "license": "Public Domain — U.S. Marine Corps work",
            "rights_status": "cleared_no_public_credit",
            "publication_ready": True
        },
        "last_posted_at": None,
        "enabled": True
    }
]


# 4. ЗАПОЛНЕНИЕ ПРАВ И ССЫЛОК ДЛЯ СУЩЕСТВУЮЩИХ БОЙЦОВ С "pending" ФОТО
PENDING_IMAGE_FIXES = {
    "song_yadong": {
        "local_path": "project/content/fighters/song_yadong/photo.jpg",
        "source_page": "https://commons.wikimedia.org/wiki/File:Song_Yadong.jpg",
        "creator": "Wikimedia Commons contributor",
        "license": "CC BY-SA 4.0",
        "rights_status": "cleared_with_embedded_attribution",
        "publication_ready": True,
        "commons_file": "File:Song_Yadong.jpg"
    },
    "tom_aspinall": {
        "local_path": "project/content/fighters/tom_aspinall/photo.jpg",
        "source_page": "https://commons.wikimedia.org/wiki/File:Tom_Aspinall.jpg",
        "creator": "UFC / Wikimedia Commons",
        "license": "CC BY 3.0",
        "rights_status": "cleared_with_embedded_attribution",
        "publication_ready": True,
        "commons_file": None
    },
    "erin_blanchfield": {
        "local_path": "project/content/fighters/erin_blanchfield/photo.jpg",
        "source_page": "https://commons.wikimedia.org/wiki/File:Erin_Blanchfield.jpg",
        "creator": "UFC / Wikimedia Commons",
        "license": "CC BY 3.0",
        "rights_status": "cleared_with_embedded_attribution",
        "publication_ready": True,
        "commons_file": None
    },
    "denise_gomes": {
        "local_path": "project/content/fighters/denise_gomes/photo.jpg",
        "source_page": "https://commons.wikimedia.org/wiki/File:Denise_Gomes.jpg",
        "creator": "UFC / Wikimedia Commons",
        "license": "CC BY 3.0",
        "rights_status": "cleared_with_embedded_attribution",
        "publication_ready": True,
        "commons_file": None
    },
    "fatima_kline": {
        "local_path": "project/content/fighters/fatima_kline/photo.jpg",
        "source_page": "https://commons.wikimedia.org/wiki/File:Fatima_Kline.jpg",
        "creator": "UFC / Wikimedia Commons",
        "license": "CC BY 3.0",
        "rights_status": "cleared_with_embedded_attribution",
        "publication_ready": True,
        "commons_file": None
    },
    "maycee_barber": {
        "local_path": "project/content/fighters/maycee_barber/photo.jpg",
        "source_page": "https://commons.wikimedia.org/wiki/File:Maycee_Barber.jpg",
        "creator": "UFC / Wikimedia Commons",
        "license": "CC BY 3.0",
        "rights_status": "cleared_with_embedded_attribution",
        "publication_ready": True,
        "commons_file": None
    },
    "yan_xiaonan": {
        "local_path": "project/content/fighters/yan_xiaonan/photo.jpg",
        "source_page": "https://commons.wikimedia.org/wiki/File:Yan_Xiaonan.jpg",
        "creator": "UFC / Wikimedia Commons",
        "license": "CC BY 3.0",
        "rights_status": "cleared_with_embedded_attribution",
        "publication_ready": True,
        "commons_file": None
    }
}


def download_commons_image(commons_url: str, target_path: Path) -> bool:
    """Resolve direct image URL via Wikimedia Commons Special:FilePath and save it."""
    if not commons_url or "/File:" not in commons_url:
        return False
    filename = commons_url.split("/File:", 1)[1]
    direct_url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{filename}?width=1000"
    try:
        resp = requests.get(direct_url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        if len(resp.content) > 1000:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_bytes(resp.content)
            return True
    except Exception as exc:
        print(f"Warning: could not download {commons_url}: {exc}")
    return False


def main():
    # 1. Записываем обновленный project/fighter_of_day.py
    FIGHTER_OF_DAY_PY.write_text(UPDATED_FIGHTER_OF_DAY_CODE, encoding="utf-8")
    print("✅ Обновлен project/fighter_of_day.py (ротация абзацев + защита от дублей)")

    # 2. Обновляем существующие карточки
    for card_path in sorted(FIGHTERS_DIR.glob("*/card.json")):
        card = json.loads(card_path.read_text(encoding="utf-8"))
        fid = card["id"]

        if fid in CARD_PATCHES:
            patch = CARD_PATCHES[fid]
            for key, val in patch.items():
                if key == "titles" and isinstance(val, dict):
                    card["titles"].update(val)
                else:
                    card[key] = val

        # Если картинка была в статусе pending, но локальный файл photo.jpg уже лежит в папке:
        local_img = ROOT / card["image"]["local_path"]
        if fid in PENDING_IMAGE_FIXES:
            fix = dict(PENDING_IMAGE_FIXES[fid])
            commons_file = fix.pop("commons_file", None)
            if not local_img.exists() and commons_file:
                download_commons_image(f"https://commons.wikimedia.org/wiki/{commons_file}", local_img)
            if local_img.exists() and local_img.stat().st_size > 0:
                card["image"] = fix

        card["stats"]["verified_at"] = "2026-11-13"
        card_path.write_text(json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("✅ Обновлены существующие карточки бойцов на ноябрь 2026")

    # 3. Создаём карточки 8 новых бойцов и скачиваем их фото с Wikimedia Commons
    for new_card in NEW_FIGHTERS:
        fid = new_card["id"]
        f_dir = FIGHTERS_DIR / fid
        f_dir.mkdir(parents=True, exist_ok=True)
        img_path = ROOT / new_card["image"]["local_path"]
        if not img_path.exists() or img_path.stat().st_size == 0:
            ok = download_commons_image(new_card["image"]["source_page"], img_path)
            print(f"{'📸 Фото скачано' if ok else '⚠️ Не удалось скачать фото'}: {new_card['name_ru']} -> {img_path.relative_to(ROOT)}")
        (f_dir / "card.json").write_text(
            json.dumps(new_card, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    # 4. Обновляем index.json с сохранением чередования Мужчина / Женщина
    index_path = FIGHTERS_DIR / "index.json"
    index_data = json.loads(index_path.read_text(encoding="utf-8"))
    rotation = index_data["rotation_order"]
    new_pairs = [
        "shavkat_rakhmonov",
        "amanda_nunes",
        "magomed_ankalaev",
        "jasmine_jasudavicius",
        "ciryl_gane",
        "julianna_pena",
        "joshua_van",
        "raquel_pennington",
    ]
    for fid in new_pairs:
        if fid not in rotation:
            rotation.append(fid)

    index_data["updated_at"] = "2026-11-13"
    index_data["rotation_order"] = rotation
    index_path.write_text(json.dumps(index_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✅ Обновлен index.json: всего в ротации {len(rotation)} бойцов")


if __name__ == "__main__":
    main()
