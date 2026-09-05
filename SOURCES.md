# MMA source validation

Validation date: 2026-09-05. Feed collection, Russian article text, images,
and source-specific cleanup have now been checked for the active sources.

## Registered candidates

| Source | Role | Feed result | Decision |
|---|---|---|---|
| UFC Official News | Official UFC announcements | HTTP 200, 30 entries, RFC date with timezone, direct UFC article URLs | Disabled until safe Russian-language handling is defined |
| ONE Championship Russian | Official Russian-language syndication | HTTP 200, 10 entries, full Russian feed content, image metadata, RFC date with timezone | Enabled; only entries with explicit MMA relevance pass the mixed-discipline feed |
| Sports.ru UFC/MMA | Russian-language MMA media | HTTP 200, 100 entries, `+03:00` dates, direct article or event-video URLs | Enabled with a 15-item limit; direct video URLs are rejected |
| MMA Fighting | International MMA reporting and corroboration | HTTP 200, 10 entries, ISO date with timezone, direct article URLs | Registered disabled until English-content handling is defined |

One UFC collector check encountered a transient TLS EOF; an immediate bounded
recheck succeeded with 20 limited, dated HTTPS entries. The feed remains
disabled because its current content is English and this project has not yet
defined a safe Russian-language transformation.

The ONE Russian feed identifies itself as an official AI-translated
syndication feed. The collector uses its full Russian entry and lead image from
the same feed response, then stops before the service paragraph `Источник`.
This avoids replacing the translation with the English article page. Its
content retains ONE attribution and is not independent confirmation of the
corresponding English article.

Sports.ru pages expose both short news and long blog material inside
`.structured-body-wrapper`. The exact-source extractor keeps structured body
paragraphs, skips bold link-only related-story promos, and never scans page
navigation or the footer. Open Graph image metadata supplies the lead image.
If that body or image is missing, the normal empty-text or text-only fallback
remains safe.

## Deferred or rejected

- ONE's MMA-only sub-feed returned HTTP 200 but no entries, so it is not useful
  as an active source yet.
- Sherdog News returned HTTP 200 with 50 dated direct links. It is a viable
  reserve source, but is not registered now because the initial list already
  has official, Russian-language, and corroborating coverage.
- MMA Junkie could not be resolved reliably from the current environment and is
  not registered.

## Activation rule

A candidate remains disabled until a saved test fixture and a live diagnostic
prove that its article body, image, footer cleanup, language handling, and
failure behavior are safe. No CAPTCHA, login wall, or anti-bot protection may
be bypassed.
