# MMA media policy

## Current image path

The active news path uses only the lead image supplied by the same source as
the article. Each post keeps the source name and direct article link. The
autoposter does not search social networks, remove watermarks, bypass access
controls, or substitute an unrelated fighter image.

The seven visual roles are `NEWS`, `FIGHTER`, `VS`, `QUOTE`, `EVENT`, `FACT`,
and `RESULT`. Current live news uses `NEWS`, `QUOTE`, `EVENT`, and `RESULT`.
Local card generation for the other roles is postponed with the evergreen
content library.

## Technical acceptance

- only credential-free HTTPS image URLs are accepted;
- JPEG, PNG, and WebP are the supported upload formats;
- the HTTP media type must agree with the downloaded file signature;
- empty files, unsupported types, and files over 10 MiB are rejected;
- an invalid or missing image produces a text post instead of blocking news;
- temporary files use the operating-system temp directory and are removed on
  success and failure;
- photo captions stay within the existing 1,000-character safety limit.

DRY_RUN downloads and validates selected images, reports their type and byte
size, deletes the temporary copies, and never calls Telegram.

## Rights and attribution

Technical availability does not by itself grant republication rights. Before
production use, the channel owner must confirm that each active source permits
the intended image use or replace the source image with licensed media. Keep
visible source branding intact and do not imply that a source endorses the
channel. Generated or composed cards must retain the provenance of every photo
and factual claim used in them.

## Native video queue

The video feature publishes at most one MP4 in each of the `day` and `evening`
slots. Every queue entry must name its source, link to the original, include a
license note, and explicitly confirm republication rights. The runner rejects
non-HTTPS locations, non-MP4 responses, invalid MP4 containers, empty files,
and files over 50 MiB. It never scrapes social networks or bypasses access
controls. DRY_RUN validates and removes the temporary download without calling
Telegram or changing video history.
