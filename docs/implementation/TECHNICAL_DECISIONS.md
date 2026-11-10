# Technical decisions

| # | Decision | Why | Alternatives considered |
|---|---|---|---|
| T1 | Keep raw parameterised SQL over `pg` (no Drizzle/Prisma) | Works, is fast and testable (`check_sql.py` executes every statement in CI); the plan's Drizzle choice was never adopted | Drizzle: rewrite cost without a measured need |
| T2 | Enforce publication in **database views** (`public_*`), not in each query | One place to get right; direct lookups can't bypass it; Typesense indexes from the same views | Per-query `WHERE production_eligible`: easy to forget (finding D2 was exactly that) |
| T3 | Evidence level is a column with CHECK constraints | The database refuses an invalid publication even if the API has a bug | App-only validation |
| T4 | PostGIS required (migration 0003) | Radius search with `ST_DWithin` + GiST, point-in-district lookup, boundaries | Haversine in SQL (did not scale) |
| T5 | Banglish search key as a generated column + pg_trgm | Postgres fallback stays useful when Typesense is down | Postgres FTS: no Bangla stemming |
| T6 | Phone OTP built in (hashed codes, per-number and per-IP limits); SMS provider pluggable | Plan's primary sign-in; no SMS credentials in this repo, so the server refuses OTP requests until a provider is configured; `SMS_PROVIDER=dev` only outside production | Firebase Auth: extra vendor |
| T7 | HS256 access tokens (15 min) + opaque rotating refresh tokens stored hashed; reuse revokes the session | Short-lived access, revocable sessions, theft detection; no extra dependency (node:crypto) | jose/passport: more surface, same result |
| T8 | Web and admin keep tokens in httpOnly cookies (BFF route handlers); CSRF by Origin check | Tokens never reach page JavaScript | Tokens in localStorage: XSS-exposed |
| T9 | Admin is a separate Next.js app (`apps/admin`, port 3001) | Plan decision; isolated bundle and auth surface | Admin routes inside the public app |
| T10 | Public pages use ISR (`revalidate`) instead of `force-dynamic`; personal pages stay dynamic | CDN-cacheable public pages (finding: everything was no-store) | — |
| T11 | Hand-written service worker, no Serwist | Small, auditable; never caches `/api`, `/me`, `/saved`, `/login` | Serwist/Workbox: another build plugin |
| T12 | Emergency page is static with a seed-generated hotline file as fallback | Must work when the API is down; only sourced numbers | — |
| T13 | Secondary token `#137a52` instead of `#16865b` | AA contrast for link text (5.0:1 vs 4.3:1) | Keep mockup value: fails WCAG |
| T14 | `production_eligible=false` for the whole nuhil hierarchy, but **shown with warnings** (product decision, 11 Nov 2026) | Never called verified; people can still find and correct their area; `noindex` keeps unchecked facts out of search engines; hotlines stay sourced-only (migration 0007). Strict mode is one env switch | Hide everything unsourced: most of the country disappears from the site |
| T15 | English locale **not** implemented; the fake language switch was removed | A real `/en` needs routing and translation of every string; a fake switch was worse than none | next-intl now: large change, see roadmap |
| T16 | Google sign-in not implemented | No OAuth credentials; cannot be tested end to end | — |
| T17 | Redis/BullMQ not introduced | Nothing needs a queue yet: reindex is a CLI, ratings are recomputed in the transaction | Add when image processing or outbox sync lands |
