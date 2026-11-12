# Final implementation report (updated 12 Nov 2026)

## A. Executive summary

The branch `claude/complete-audit-report-1016dc` turns the read-only Phase 1 slice into a trust-first platform:

- data rules enforced in the database;
- a reconciled seed;
- accounts, contributions, moderation and verification;
- a separate admin app;
- a bilingual (Bangla at `/`, English at `/en`) PWA public site with offline emergency information;
- staff two-factor authentication, duplicate detection and a keyed Open Data API;
- CI covering lint through browser tests.

**It is not production-ready yet, and that is deliberate:**

- **Official evidence covers Rajshahi Division only:**
  - Rajshahi Division's 8 districts, 67 upazilas, 566 unions, 62 pourashavas and 618 wards now have official evidence (BBS 2022, LGD and government portals).
  - 21,113 places from government registers are added (see [COLLECTED_DATA.md](../data/COLLECTED_DATA.md)).
  - The other seven divisions still rely on a community dataset. They are shown with "not verified" warnings and `noindex`.
- **No SMS gateway:** the sign-in SMS gateway is not configured.
- **Not deployed:** nothing has been deployed.

## B. Repository changes

- 8 commits on top of `548bed0` (`main`): 274 files changed.
- **New migrations (additive):** `0002_data_trust`, `0003_postgis_search`, `0004_accounts_workflow`, `0005_public_views`, `0006_session_rotation_grace`, `0007_hotlines_always_sourced`, `0008_staff_2fa`, `0009_open_data_keys`. `0001` is unchanged.
- **New app:** `apps/admin`.
- **New in `apps/api`:** auth, me, reviews, contributions, admin (4 controllers), contact, common (problem filter, request context, auth guard, permissions, tokens), CLI `grant-role`.
- **Data:**
  - `data/sources/master_v3` (compact copy, no zips).
  - `pipelines/{trust,reconcile,validate_seed,test_pipeline}.py`.
  - Generated `docs/data/{SOURCE_REGISTRY,UNRESOLVED_CONFLICTS}.md`.
- **Tooling:** `eslint.config.mjs`, `playwright.config.ts`, `tests/e2e/*`, `scripts/{db-migrate.sh,integration-api.test.mjs}`.
- **Dependencies added:**
  - API: `helmet`, `@nestjs/throttler`, `@nestjs/swagger`.
  - Root dev: `eslint`, `@eslint/js`, `typescript-eslint`, `globals`, `@playwright/test`.
  - Web: `next-intl` (`~4.4`).
  - `pnpm-lock.yaml` is now committed.
- **Removed:** the fake language switch and the static bell icon from the web header.

## C. Data quality

| Item | Before | After |
|---|---|---|
| Records marked verified + production-eligible on community data alone | 5,099 (unions, upazilas, districts) | 0 |
| Sourced (eligible) areas | everything claimed | 1,399: Rajshahi Division (1,322 official) plus country, divisions, districts and city corporations; the rest are shown with warnings |
| Sourced places / hotlines | 8 / 10 claimed | 21,112 places (official registers; 1 pilot place still unsourced) / 7 hotlines |
| Duplicate unions | 3 | 0 |
| Junk names | 5 | 0 |
| Unicode | mixed forms | NFC everywhere |
| Natore Naldanga unions | 0 (under Sadar) | 5 (per district administration) |
| Seed vs master v3.0 | not compared | Tracked differences, each with a master conflict id; Bagha, Ullapara, Gabtali and Bhangura resolved by official evidence; CI fails on new or stale ones |
| Rajshahi Division boundaries | districts only | 67 upazilas, 540 unions, 14 pourashavas, 28 wards (geoBoundaries / HDX) |
| Wikipedia mirror links | 3 | 0 |

Policy: [DATA_TRUST_POLICY.md](../data/DATA_TRUST_POLICY.md). Reconciliation: [DATA_RECONCILIATION.md](../data/DATA_RECONCILIATION.md). Open conflicts: [UNRESOLVED_CONFLICTS.md](../data/UNRESOLVED_CONFLICTS.md).

## D. Backend

- **Public reads:** every read goes through the `public_*` views. New endpoints: `/areas/:id/stats`, `/areas/tree`, `/areas/:id/boundary`, `/geo/locate`, `/search/suggest`, `/contact`. Search gains type/level/category/area filters, and place lists return totals.
- **PostGIS:** radius search (`ST_DWithin` + GiST), district boundaries, point-in-district lookup.
- **Search:** Banglish key plus trigram fallback, and a Typesense circuit breaker.
- **Auth:**
  - Phone OTP: codes are hashed, expire in 5 minutes, allow 5 attempts, and are limited to 3 per number per 15 minutes plus a per-IP limit.
  - Tokens: HS256 access tokens (15 min) and rotating refresh tokens stored hashed.
  - Reuse of an old refresh token revokes the session, with a 30 s grace window for parallel requests.
  - Logout works for one device or all devices.
- **Users:** profile, deletion request, saved items and collections, reviews (with reports), and contributions (draft → submitted → in review → needs changes / approved / rejected, with history).
- **Admin API:** a permission matrix over 10 roles, geographic scope, verification enforcing the policy, moderation, sources, users, and an append-only audit log with before/after records.
- **Security baseline:** Helmet + CSP, rate limits, RFC 9457 errors, request ids, structured logs without query strings, statement timeout, OpenAPI at `/docs`.

## E. Frontend (apps/web)

- **Trust display:** evidence badges (only official evidence says "verified"), area pages disclose pending child areas, and every page has a source footer with a report link.
- **Accounts:** sign-in, profile, saved items, a reviews form, and a 4-step contribution wizard with offline drafts.
- **Emergency:** a static page with a bundled fallback, quick tiles, and a 999 button visible on phones.
- **Navigation:** search suggestions and filters, true category totals with paging.
- **Map fixes:** the selected category survives load, tile errors show a message, pin colours come from the tokens, and place pages get a mini map.
- **Live map (`/map`, 12 Nov 2026):**
  - Rajshahi District first, with a switch to the whole division.
  - Upazila and union outlines come from `GET /v1/areas/:id/boundaries`.
  - Places load for the visible area and refresh every minute, with category filters and counts of what is in view.
  - Clicking an area shows its population and place list, including places with no map location yet.
  - The maps on the home and area pages rendered at zero height: MapLibre's CSS overrode `absolute inset-0`. Fixed. The cluster labels now use the basemap's Noto Sans font, which removes the font 404.
- **PWA:** manifest, icons, service worker, offline page, update and offline banners.
- **Static pages:** About, Contact, Privacy, Terms, Data policy, Guidelines.
- **Tokens:** AA contrast, a full dark theme with a toggle, distinct category colours.
- **Caching:** ISR for public pages, with security headers.
- **English:** every page at `/en/...` (next-intl message catalogs, hreflang, canonical URLs, a real language switch). Bangla stays at `/` with unchanged URLs, and caching is unchanged (ISR area/place pages, static `/emergency`).

## F. Admin (apps/admin)

- **Dashboard:** live stats.
- **Verification centre:** queue of unpublished areas and places.
- **Records:** areas (edit, re-parent, verify), places (create, edit, verify).
- **Moderation:** queue with decisions; approval creates an unpublished place.
- **Other pages:** review reports, sources, audit log with field diffs, users (role, scope, status).
- **Security:** httpOnly-cookie BFF and Origin-checked mutations.
- **Staff 2FA:** TOTP (RFC 6238) with encrypted secrets, replay protection, 8 single-use recovery codes and lockout. With `STAFF_REQUIRE_2FA` (on by default in production) the admin app shows an enrolment/code gate before any page.
- **Duplicates:** name + 500 m distance scoring on new places, contributions and full re-scans. Scores ≥ 95 block publication until a staff decision; merging archives the copy and moves its reviews and saves.
- **Open Data keys:** issue (shown once) and revoke.

## G. Security and performance

- **Security:** see D. CSRF uses Origin checks in both Next apps, and tokens are never readable from JavaScript.
- **Not done:** CAPTCHA, upload scanning (there are no uploads).
- **First-load JS:** 103–114 kB per public route, within the 170 kB budget. Area, place and home pages are ISR; the emergency page revalidates hourly.

## H. Testing (actual results from this session)

| Check | Result |
|---|---|
| `pnpm install --frozen-lockfile` | Pass |
| `pnpm build` (5 tasks) / `pnpm typecheck` (7) | Pass |
| `pnpm lint` (4 packages) + `pnpm lint:root` | Pass, 0 problems |
| Unit: shared 7, api 8 (incl. RFC 6238 TOTP vectors, duplicate thresholds), pipeline 6 | Pass |
| `validate_seed.py` | 0 failures, 4 warnings (±1 population rounding); also checks source manifests and checksums |
| Seed rebuild reproducible | Pass |
| `check_sql.py` | 45/45 statements OK (with 21,113 places loaded) |
| `db-migrate.sh` on an empty DB, rerun, and tampered file | Applies 0001–0009 / "up to date" / aborts with exit 3 |
| API integration (`integration-api.test.mjs`) | 9/9 pass in labelled (default) mode with Typesense, on the 12 Nov seed |
| API smoke / web smoke | All checks pass (API smoke in both modes) |
| Playwright (Pixel 7 + desktop: public, account, English, admin incl. 2FA enrolment and key issuing) | 46 passed, 2 skipped (admin tests on mobile, by design); 3 needed a rerun after the dev API's sign-in rate limit |
| Lighthouse (mobile): home / place / emergency | Accessibility 100/100/100 · SEO 100/100/100 · Best practices 96/96/100. The two 96s come from a third-party basemap font 404 |
| Typesense search path | Pass locally (typo-tolerant, Banglish, Bangla prefix); circuit breaker fails over to Postgres in < 70 ms and recovers |
| GitHub Actions | **Not yet run**; first run happens on push |

Bugs found and fixed by these tests:
- with 21k places, "nearby" could list places out of distance order (sphere vs spheroid distance) and duplicate detection could miss the strongest match (no ordering before `LIMIT 20`);
- the refresh-reuse revoke was rolled back;
- parallel refreshes could log users out;
- stale fetch cache crashed the evidence badge;
- the reviews fetch broke ISR;
- cards overflowed at phone width;
- three admin SQL statements had enum/text type clashes.

## I. Git

- **Branch:** `claude/complete-audit-report-1016dc`. `main` is untouched.
- **Commits:** `9b5f865`, `97345a2`, `8bac67d`, `7370af1`, `525e639`, `b95e3a3`, `2bc7608`, `e66448f`, plus this report's commit.
- **Size:** the largest tracked file is 4.0 MB. The 238 MB master zip and archives are excluded (`.gitignore`).
- **Push status:** see the final message of the session.

## J. Production readiness

| Area | Status |
|---|---|
| Data trust enforcement | Complete (labelled visibility by default; strict mode available) |
| Official verification of data | Partially complete (Rajshahi Division from official sources; seven divisions to go) |
| Master reconciliation | Partially complete (Rajshahi Division conflicts mostly resolved; see UNRESOLVED_CONFLICTS.md) |
| Public API, search, geo | Complete (Typesense untested locally) |
| Auth | Partially complete. **Blocked** on an SMS gateway; Google sign-in not started (no OAuth credentials). Staff 2FA complete |
| User features (saved, reviews, contributions) | Complete (collections UI and photo uploads not started) |
| Admin + moderation + verification + duplicates | Complete |
| Open Data API | Complete (live, keyed, sourced-only); release-pinned bulk files not started |
| Public website | Complete in Bangla and English |
| PWA/offline | Partially complete (no offline district packs, no background sync) |
| Security baseline | Complete (CAPTCHA, upload scanning not started) |
| Observability | Partially complete (logs, request ids, health; no Sentry/metrics) |
| CI | Complete locally; first GitHub run pending |
| Deployment | **Not started** (procedure in `docs/DEPLOYMENT.md`) |
