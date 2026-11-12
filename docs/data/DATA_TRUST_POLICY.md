# Data trust policy

Elaka360 shows every record with the evidence behind it, and treats a record as **sourced** (production-eligible) only when it can name where the fact comes from. This page is the rule the code enforces.

## Evidence levels

| Level | Meaning | Examples | Can be published? | Public label |
|---|---|---|---|---|
| `official` (Tier 1) | Checked against a primary government source, with its official identifier where one exists | Gazette, LGD union list, BBS publication, ministry portal (source trust 4–5) | Yes, after review | সরকারিভাবে যাচাইকৃত |
| `secondary` (Tier 2) | Taken from a reliable secondary source with attribution | Wikipedia, census compilations (citypopulation.de), national newspapers (trust 3) | Yes, after review | দ্বিতীয় উৎস থেকে নেওয়া |
| `community` (Tier 3) | Community dataset or user submission | nuhil/bangladesh-geocode, approved contributions | Shown with a warning, never counted as sourced | কমিউনিটির তথ্য |
| `unverified` | No usable source yet | General knowledge, mockups | Shown with a warning, never counted as sourced | যাচাই বাকি |

Only `official` may be called "verified" on its own. The legacy `verified` column is true only for `official` records.

## Enforced rules

1. **Database constraints** (`db/migrations/0002_data_trust.sql`): `production_eligible` requires `official` or `secondary` evidence **and** an evidence source. `verified` requires `official`. Coordinates must fall inside Bangladesh. New records default to not eligible.
2. **One read path** (`0005_public_views.sql`): every public API query reads `public_admin_areas`, `public_places`, `public_emergency_numbers` or `public_reviews`; the visibility switch below decides whether non-eligible records are included. Search indexes are built from the same views. Every response carries `evidence_level` and `production_eligible`.
3. **Verification API** (`POST /v1/admin/{areas,places}/:id/verify`): rejects publishing community or unverified evidence. It also rejects official evidence from a source below trust 4, and publication without a source URL. A note saying what was checked is required.
4. **Edits re-open verification**: changing names, location, category or contact details of a published place, or renaming a published area, unpublishes it until it is re-verified.
5. **Contributions never publish directly**: an approved new-place suggestion becomes an unpublished place with `community` evidence. A verifier must attach a source before it can go public.
6. **Nothing is inherited**: a verified district does not make its upazilas verified, and vice versa.
7. **Seed validation** (`pipelines/validate_seed.py`, run in CI) fails if any seed row breaks rules 1 or 6.

## Visibility (product decision, 11 Nov 2026: show with labels)

By default (`PUBLIC_INCLUDE_UNVERIFIED` unset or `true`) the public site **shows** records that are not production-eligible so people can find their area and correct it. Every such record is labelled:

- area and place pages open with a "যাচাই করা হয়নি" (not verified) warning and a report link;
- cards carry the evidence badge;
- the pages send `robots: noindex`, so search engines do not spread unchecked facts;
- home-page counts show the sourced subset (`/v1/stats/national` → `sourced`).

Exceptions that never show unsourced data, in any mode:

- **Emergency hotlines** (`0007_hotlines_always_sourced.sql`). An unverified number is never a tap-to-call link.
- **Open Data exports** (planned) must use only production-eligible rows.

`PUBLIC_INCLUDE_UNVERIFIED=false` switches to strict mode: non-eligible records return 404 and are left out of lists, search and counts. CI tests both modes.

## What changed in November 2026

The v0.1 seed marked the whole nuhil hierarchy as verified and production-eligible. That is 4,540 unions, 495 upazilas and 64 districts. Under this policy:

| Level | Sourced (eligible) | Not yet sourced (shown with a warning) | Evidence |
|---|---|---|---|
| Divisions | 8 | 0 | secondary (citypopulation.de, BBS 2022) |
| Districts | 64 | 0 | secondary (citypopulation.de, BBS 2022) |
| Upazilas | 10 (Rajshahi's 9 + Shayestaganj) | 485 | secondary / community |
| City corporations | 13 | 0 | secondary (Wikipedia, The Financial Express) |
| Unions | 0 | 4,538 | community (one secondary, Brahmandura, held back) |
| Pourashavas | 0 | 14 | unverified |
| Places | 5 | 3 | secondary / unverified |
| Hotlines | 7 | 3 (16263, 1098, 16430) | secondary / unverified |

The full before/after table is `data/seed/qa/verification_changes.csv`. The original source references are kept on every row.
