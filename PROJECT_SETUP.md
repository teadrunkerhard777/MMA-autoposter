# How to create a new autoposter from this template

The first safe local version should take about 15–30 minutes. Keep the local
static source enabled until your project rules and output are covered by tests.

## Step 1 — Copy the template

Copy this directory without its `.git` folder, then initialize a new repository.

```bash
cp -R autoposter-template my-autoposter
cd my-autoposter
rm -rf .git
git init
```

## Step 2 — Rename the project

Update the title in `README.md`, workflow `name`, concurrency group in
`.github/workflows/autoposter.yml`, and lock name passed in `main.py` if several
autoposters can run on the same machine.

## Step 3 — Configure project settings

Edit `project/settings.py`:

- `NEWS_LOOKBACK_DAYS` controls freshness;
- `MAX_NEWS_PER_RUN` limits one run;
- `MIN_PUBLICATION_SCORE` sets the project threshold;
- `EVENT_DEDUP_SETTINGS` tunes conservative event matching.

Keep the initial publication limit small.

## Step 4 — Add sources

Edit `project/sources.py`. RSS is declarative:

```python
{
    "name": "Vendor engineering blog",
    "type": "rss",
    "url": "https://example.com/feed.xml",
    "enabled": True,
}
```

HTML category pages use CSS selectors:

```python
{
    "name": "Example news page",
    "type": "html",
    "url": "https://example.com/news",
    "base_url": "https://example.com",
    "item_selector": "article.card",
    "title_selector": "h2 a",
    "link_selector": "h2 a",
    "date_selector": "time[datetime]",
    "description_selector": "p.summary",
    "enabled": True,
}
```

Use direct, free RSS or maintainable HTML pages. Do not bypass anti-bot systems.

## Step 5 — Define relevance

Edit `project/filters.py`. `is_relevant(news_item)` may annotate the item but
must return a boolean. It should set an `event_category` for event deduplication:

```python
def is_relevant(news_item):
    text = f"{news_item['title']} {news_item['description']}".casefold()
    accepted = "release" in text
    news_item["event_category"] = "release" if accepted else None
    news_item["event_locations"] = []  # Optional signal.
    return accepted
```

Core does not know or decide what your channel considers relevant.

## Step 6 — Define scoring

Edit `project/scoring.py`. Return an integer; generic processing attaches it and
sorts candidates:

```python
def calculate_score(news_item):
    return 5 if "major" in news_item["title"].casefold() else 1
```

Scoring should rank relevant items, not bypass the relevance filter.

## Step 7 — Format posts

Edit `project/formatter.py`. Keep both functions:

- `format_post(news_item)` for `sendMessage`;
- `format_photo_caption(news_item)` for `sendPhoto`.

Escape user/source HTML, preserve the source URL, and stay inside Telegram's
text and caption limits. `generation/text.py` provides a safe trimming helper.

## Step 8 — Create a local environment file

Copy `.env.example` to `.env` and leave safe mode enabled:

```text
AUTOPOSTER_DRY_RUN=true
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

`.env` is ignored by Git. Never commit real secrets.

## Step 9 — Run tests

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest
```

Add project regression tests for accepted and rejected stories, scoring ties,
and final Telegram formatting before enabling real sources.

## Step 10 — Run DRY_RUN

```bash
AUTOPOSTER_DRY_RUN=true .venv/bin/python main.py
```

Inspect collected, fresh, relevant, scored, unique, new, and selected counts.
Confirm the post text is correct and `storage/published.json` remains `[]`.

## Step 11 — Configure Telegram

Create a bot through Telegram's official BotFather, add it to the target channel,
and grant only the permissions needed to post. Put the token/chat ID in local
`.env` for a deliberately authorized test; never paste them into source code.

## Step 12 — Add GitHub Secrets

In repository settings, create:

- `TELEGRAM_BOT_TOKEN`;
- `TELEGRAM_CHAT_ID`.

Do not add `AUTOPOSTER_DRY_RUN` as a secret; the workflow explicitly sets its
production value near the run command where reviewers can see it.

## Step 13 — Enable GitHub Actions

Review `.github/workflows/autoposter.yml`. It runs tests, runs the autoposter,
and commits only `storage/published.json` when publication succeeds. Keep
`workflow_dispatch`, `cancel-in-progress: false`, and history-only staging.

Run it manually only after a safe local review. A manual workflow run with the
example file is production mode and can send when valid secrets are present.

## Step 14 — Connect an external scheduler

Use a trusted external scheduler to call GitHub's `workflow_dispatch` API. The
template intentionally has no GitHub `schedule` block. Configure one scheduler
only, choose a conservative interval, and verify workflow concurrency before
leaving it unattended.

## Source-specific article extraction

When a site needs a reliable body selector, add a small function in
`project/sources.py` and register it in `SOURCE_EXTRACTORS`:

```python
def extract_vendor_article(soup):
    body = soup.select_one("article .body")
    if body is None:
        return ""
    return "\n\n".join(
        p.get_text(" ", strip=True) for p in body.select("p")
    )

SOURCE_EXTRACTORS = {"Vendor blog": extract_vendor_article}
```

Use `SOURCE_STOP_MARKERS` only for a verified source footer. Never turn a local
HTML defect into an aggressive global cleanup rule.

