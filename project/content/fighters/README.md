# Fighter of the Day content base

Each fighter has a separate `card.json` in a stable ID directory. `index.json`
defines the editorial order and keeps the initial male/female alternation explicit.

The factual source links are internal editorial metadata. They must not be added
to Telegram posts. Titles are split into `current`, `former`, and `other` groups.
Current fight statistics carry their own `verified_at` date.

An image is publishable only when `publication_ready` is `true` and
`rights_status` is `cleared_no_public_credit`. Until a real photo is licensed for
publication without a mandatory public credit, the card keeps a planned local
path and uses `pending` rights status. A future runner must skip cards whose image
is not publication-ready; it must not silently substitute a copyrighted image.
