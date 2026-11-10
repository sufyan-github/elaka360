# Feature inventory

Status words: **Complete** (built, wired end to end, tested), **Partial** (works, with listed gaps), **Blocked** (needs something outside the repo), **Not started**.

| Module | Before (548bed0) | Now | Evidence | Gaps |
|---|---|---|---|---|
| Data trust model | Missing | Complete | Migrations 0002/0005, `validate_seed.py`, integration test 1 & 6 | No official evidence exists yet (needs LGD/BBS work) |
| Master v3.0 reconciliation | Not merged | Partial | `pipelines/reconcile.py`, `docs/data/*` | 16 tracked differences need primary evidence |
| Geography API | Partial | Complete | `/areas*`, `/areas/:id/stats`, `/areas/tree`, `/areas/:id/boundary`, `/geo/locate` | Boundaries only for districts |
| Places API (public) | Partial | Complete | List with totals, nearby (PostGIS), bbox pins, detail | — |
| Search | Partial | Complete (Postgres) / Partial (Typesense) | Integration test 3 | Typesense path runs in CI only (no local image) |
| Auth (phone OTP) | Missing | Partial | Integration test 4, Playwright account tests | **Blocked**: no SMS gateway; Google sign-in not built; no admin 2FA |
| Profile, saved, collections | Missing | Partial | Playwright; `/me`, `/saved` | Collections API only (no collections UI); no offline packs |
| Reviews | Missing | Complete | Integration test 5, Playwright | Review edit UI only via API |
| Contributions | Missing | Complete | Wizard, drafts, history; integration test 5 & 6 | Photo uploads not built (no media storage) |
| Moderation + verification | Missing | Complete (API) | Integration test 6 | Duplicate detection/scoring not built |
| Admin app | Missing | see final report | `apps/admin` | |
| Sources registry | CSV only | Complete | Admin API + generated `SOURCE_REGISTRY.md` | Licences missing for several sources |
| Audit log | Table only | Complete | Append-only trigger; every admin mutation writes before/after | — |
| Roles + geographic scope | Missing | Complete | Permission matrix; scope test in integration 6 | — |
| Emergency | Partial | Complete | Static + fallback; Playwright | Nearby emergency map uses generic near-me |
| PWA / offline | Missing | Partial | Manifest, SW, offline page | No district offline packs, no background sync |
| i18n (English) | Missing | Not started | Fake switch removed | `/en` routes + translations |
| Security baseline | Missing | Complete | Helmet/CSP, rate limits, problem details, CSRF, request ids | No CAPTCHA, no upload scanning (no uploads) |
| Observability | Minimal | Partial | JSON access logs, request ids, `/health` | No Sentry/OTel/metrics backend |
| CI | Partial | Complete | Lint, unit, SQL, integration, smoke, Playwright, migrations | Lighthouse not in CI (run manually) |
| Media (photos) | Missing | Not started | — | Needs S3/R2 credentials |
| Jobs (BullMQ) | Missing | Not started | — | Not needed yet |
| Open Data API | Missing | Not started | — | Eligibility views make it straightforward |
