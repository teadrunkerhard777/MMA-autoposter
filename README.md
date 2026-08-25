# Autoposter Template

A small, reusable Python template for rule-based Telegram news autoposters.
It separates stable infrastructure from the theme of a particular channel and
keeps local execution safe by default.

## What it includes

- RSS, declarative HTML, and local static collectors.
- A shared `news_item` data shape.
- Date filtering, project-owned relevance, scoring, and stable ranking.
- URL, title, and conservative cross-source event deduplication.
- Generic article text and `og:image` / `twitter:image` extraction.
- Isolated source-specific article extractors and stop markers.
- Telegram text/photo publishing with temporary-file fallback.
- Duplicate protection for uncertain Telegram network outcomes.
- JSON publication history with backward-compatible fingerprints.
- Safe `DRY_RUN=True`, a local process lock, tests, and GitHub Actions.

No paid API, AI service, database, browser automation, or framework is needed.

## Architecture

```text
reusable infrastructure             channel-specific behavior
core/ collectors/ processing/       project/sources.py
article/ generation/ publishing/ +  project/filters.py
storage/                             project/scoring.py
                                     project/formatter.py
                                     project/settings.py
```

`main.py` composes these two layers with ordinary Python functions. There is no
plugin framework or dependency-injection container.

## Quick start

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
.venv/bin/python -m pytest
.venv/bin/python main.py
```

The included ExampleNews project uses local synthetic technology news. The
first run therefore demonstrates the full selection and formatting pipeline
without network access, Telegram calls, or history writes.

To build a real channel, follow [PROJECT_SETUP.md](PROJECT_SETUP.md). For the
design and LiveCrime mapping, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Safety

`AUTOPOSTER_DRY_RUN` defaults to `true`. A live Telegram send requires all of:

1. `AUTOPOSTER_DRY_RUN=false`;
2. valid `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`;
3. an explicit execution of `main.py`.

Do not use real credentials in committed files. The example workflow reads
credentials only from GitHub Secrets and has no built-in schedule.

