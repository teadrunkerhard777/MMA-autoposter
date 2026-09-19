# MMA Autoposter

A rule-based Telegram autoposter for an energetic Russian-language MMA channel.
It is being built in small verified stages on top of a reusable autoposter
template and keeps local execution safe by default.

## What it includes

- RSS, declarative HTML, and local static collectors.
- A shared `news_item` data shape.
- Date filtering, project-owned relevance, scoring, and stable ranking.
- Canonical URL, title, fighter-pair, and cross-source event deduplication.
- Generic article text and `og:image` / `twitter:image` extraction.
- Isolated source-specific article extractors and stop markers.
- Project-owned visual roles and validated DRY_RUN image previews.
- Telegram text/photo publishing with temporary-file fallback.
- Two daily native-video slots at 13:00 and 20:00 Asia/Yekaterinburg,
  dynamically filled from Pexels and Pixabay.
- Duplicate protection for uncertain Telegram network outcomes.
- JSON publication history with backward-compatible fingerprints.
- Safe `DRY_RUN=True`, a local process lock, tests, and GitHub Actions.

No paid API, AI service, database, browser automation, or framework is needed.

See `MEDIA_POLICY.md` before enabling production image publication.
See `EDITORIAL_POLICY.md` for the strict publication-priority order.

## Architecture

```text
reusable infrastructure             channel-specific behavior
core/ collectors/ processing/       project/sources.py
article/ generation/ publishing/ +  project/filters.py
storage/                             project/scoring.py
                                     project/formatter.py
                                     project/scheduling.py
                                     project/selection.py
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

The current Stage 2 project uses local synthetic MMA stories. A run therefore
demonstrates MMA relevance, event-date priority, rumor labels, scheduled
evergreen slots, scoring, and Russian formatting without network access,
Telegram calls, or history writes.

To build a real channel, follow [PROJECT_SETUP.md](PROJECT_SETUP.md). For the
design and LiveCrime mapping, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Safety

`AUTOPOSTER_DRY_RUN` defaults to `true`. A live Telegram send requires all of:

1. `AUTOPOSTER_DRY_RUN=false`;
2. valid `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`;
3. an explicit execution of `main.py`.

Do not use real credentials in committed files. The included workflows read
credentials only from GitHub Secrets. News and Fighter of the Day remain
manual. The video workflow runs twice daily, alternates Pexels and Pixabay
with automatic fallback, and skips safely if its API keys are unavailable or
no unused suitable clip is found. Add `PEXELS_API_KEY` and `PIXABAY_API_KEY`
to GitHub Actions secrets.
