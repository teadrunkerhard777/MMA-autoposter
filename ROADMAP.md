# MMA Autoposter Roadmap

Roadmap translates `PROJECT_CONCEPT.md` into small, independently testable
stages. Every stage keeps `AUTOPOSTER_DRY_RUN=true` unless a later task
explicitly authorizes a Telegram test.

## Baseline audit

Status on 2026-09-05:

- the reusable template is intact and cleanly separated from `project/`;
- all 70 template tests pass on Python 3.14.6;
- the local ExampleNews DRY_RUN completes successfully;
- Telegram is not called and `storage/published.json` stays unchanged;
- the repository is still configured as the ExampleNews demonstration;
- MMA sources, relevance rules, scoring, formatting, and settings have not yet
  been implemented;
- the current core supports news collection and publication, but evergreen
  formats such as Fighter of the Day, VS, Fact, and MMA History require later
  project-level producers and data sources.

## Stage 1: Local MMA editorial MVP

Status: complete. The repository now has a local-only MMA editorial layer; live
source work remains in Stage 3.

Replace the ExampleNews project configuration with a safe local MMA fixture.
Implement project-owned MMA relevance, content categories, rumor handling,
scoring, Russian Telegram formatting, and initial run limits.

Scope:

- edit only `project/`, focused project tests, and project-facing docs;
- keep one enabled local static source and no enabled network sources;
- recognize a small explicit set of meaningful MMA event categories;
- reject clearly unrelated sports and general news;
- mark rumors explicitly and prevent rumor wording from becoming fact;
- rank major UFC/MMA events and priority fighters above weak stories;
- produce concise Russian posts with a visible source link;
- select up to five strong items per run without publishing them.

Acceptance:

- focused MMA tests cover acceptance, rejection, categorization, rumor labels,
  scoring, HTML escaping, and caption limits;
- the full test suite passes;
- DRY_RUN prints MMA output only;
- Telegram is not called;
- the publication-history hash is unchanged.

## Stage 2: Event priority and scheduled content

Implement the agreed editorial model locally before choosing live sources.
Separate reactive news candidates from pre-produced scheduled content and add
project-owned handling for `event_at` and `scheduled_at`.

Priority order:

1. confirmed events in the next 0–48 hours;
2. confirmed events in the next 3–7 days;
3. major breaking stories, conflicts, and other current news;
4. one or two scheduled evergreen posts per day.

Known cancellations, injuries, and urgent card changes may override the normal
order. Evergreen formats include fighter profiles, women in MMA, facts,
matchups, and history; attractive presentation must not replace sourced sports
facts.

Acceptance:

- `published_at`, `event_at`, and `scheduled_at` have distinct semantics;
- proximity bonuses apply only to reliable timezone-aware `event_at` values;
- 0–48 hour events rank above otherwise comparable 3–7 day events;
- urgent cancellations or injuries can outrank ordinary previews;
- one or two eligible evergreen slots can be selected without filling the feed
  with weak news;
- scheduled items cannot be selected before `scheduled_at`;
- deterministic local tests and DRY_RUN cover both queues.

## Stage 3: Free source shortlist and collector validation

Select several free, complementary sources: official promotions first, then
reputable MMA media. Verify RSS availability, publication dates, direct article
URLs, access reliability, and image metadata before enabling each source.

Acceptance:

- no CAPTCHA or anti-bot bypass;
- one failing source cannot stop the run;
- collector tests use saved fixtures, never live network services;
- enabled sources provide timezone-aware dates and direct article URLs.

## Stage 4: Article extraction and source quality

Validate article body and image extraction for every enabled source. Add exact
source-specific extractors or stop markers only for reproduced defects.

Acceptance:

- each article is fetched once for text and image;
- navigation, promotional blocks, and footers do not enter posts;
- source-specific fixes do not alter unrelated sources;
- missing text or image degrades safely.

## Stage 5: Event identity, freshness, and deduplication

Tune Russian and English event fingerprints, fighter aliases, categories, and
time windows. Keep article publication time distinct from event freshness when
reliable event data is available.

Acceptance:

- URL, title, cross-source event, and publication-history duplicates are
  covered by regression tests;
- an old event republished by a new site does not become fresh automatically;
- unrelated fights involving the same promotion are not merged.

## Stage 6: Editorial mix and evergreen content

Add project-level data and producers for Fighter, VS, Fact, Quote, Event,
Result, and MMA History posts. Use only traceable facts and real sourced quotes.

Acceptance:

- weak news is not published to fill a quota;
- quiet days can use verified evergreen material;
- every quote and factual card retains provenance;
- content-mix selection remains deterministic and testable.

## Stage 7: Visual pipeline

Define NEWS, FIGHTER, VS, QUOTE, EVENT, FACT, and RESULT image paths. Start with
reliably sourced article images and reusable local card composition; do not make
paid or AI image APIs required dependencies.

Acceptance:

- mobile readability and caption limits are verified;
- missing or invalid images fall back to text safely;
- temporary files are always removed;
- media rights and source attribution rules are documented.

## Stage 8: Test-channel validation

After explicit authorization, configure credentials locally and make a limited
test-channel run. Preserve the publisher's confirmed-versus-uncertain delivery
semantics and update history only after confirmed success.

Acceptance:

- full tests pass immediately before the run;
- only the explicitly selected test item is sent;
- Telegram result and history update agree;
- no credential or Bot API URL appears in output or Git.

## Stage 9: Production scheduling and observation

Enable the production channel only after editorial review of repeated DRY_RUN
results. Add conservative scheduling, concurrency protection, and operational
reporting without expanding the architecture into a framework.

Acceptance:

- 4–8 daily posts is a target, never a forced quota;
- large-event days and quiet days have documented behavior;
- failures are isolated and visible;
- rollback means disabling the schedule or restoring DRY_RUN, not rewriting
  publication history.

## Stage discipline

For every stage:

1. use one narrowly scoped Codex task;
2. inspect user-owned changes before editing;
3. make the smallest project-layer change that satisfies the stage;
4. add focused regression tests;
5. run focused tests and the full suite;
6. run an end-to-end diagnostic only with effective DRY_RUN enabled;
7. compare `storage/published.json` before and after;
8. inspect the complete diff and run `git diff --check`;
9. report settings, tests, Telegram activity, history state, and Git state;
10. commit the completed stage without including unrelated files.
