# MMA source validation

Validation date: 2026-09-05. These checks cover public feed collection only;
article-body and image validation belongs to Stage 4.

## Registered candidates

| Source | Role | Feed result | Decision |
|---|---|---|---|
| UFC Official News | Official UFC announcements | HTTP 200, 30 entries, RFC date with timezone, direct UFC article URLs | Registered disabled until article extraction is verified |
| ONE Championship Russian | Official Russian-language syndication | HTTP 200, 10 entries, RFC date with timezone, direct ONE article URLs | Registered disabled; filter to MMA because the feed also covers other combat sports |
| Sports.ru UFC/MMA | Russian-language MMA media | HTTP 200, 100 entries, `+03:00` dates, direct article or event-video URLs | Registered disabled; promotional and duplicate entries need Stage 4 review |
| MMA Fighting | International MMA reporting and corroboration | HTTP 200, 10 entries, ISO date with timezone, direct article URLs | Registered disabled until English-content handling is defined |

One UFC collector check encountered a transient TLS EOF; an immediate bounded
recheck succeeded with 20 limited, dated HTTPS entries. This reinforces the
decision to keep the feed disabled until Stage 4 verifies its complete fetch
path and failure behavior.

The ONE Russian feed identifies itself as an official AI-translated
syndication feed. Its content must retain source attribution and must not be
treated as independent confirmation of the corresponding English ONE article.

## Deferred or rejected

- ONE's MMA-only sub-feed returned HTTP 200 but no entries, so it is not useful
  as an active source yet.
- Sherdog News returned HTTP 200 with 50 dated direct links. It is a viable
  reserve source, but is not registered now because the initial list already
  has official, Russian-language, and corroborating coverage.
- MMA Junkie could not be resolved reliably from the current environment and is
  not registered.

## Activation rule

A candidate remains disabled until a Stage 4 fixture proves that its article
body, image, footer cleanup, language handling, and failure behavior are safe.
No CAPTCHA, login wall, or anti-bot protection may be bypassed.
