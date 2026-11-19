# Repository audit: baseline before implementation (11 Nov 2026)

Baseline commit `548bed0` on `main`. The plan audit report (Claude Doc "Elaka360 — Plan Audit Report") was re-checked against the code before anything changed.

## Baseline checks

| Check | Result at 548bed0 |
|---|---|
| `pnpm install --frozen-lockfile` | **Fail**: no lockfile committed |
| `pnpm install` (as CI ran it) | Pass |
| `pnpm build` / `pnpm typecheck` | Pass |
| `pnpm test` | Pass (shared 7, api 3; web had none) |
| Lint | Not configured |
| `db-reset` + `check_sql.py` | Pass (18 statements) |
| Seed reproducible | Pass |
| API / web smoke | Pass on the Postgres search path; Typesense path not testable locally |

## Audit findings re-verified

| Finding | Re-check | Notes |
|---|---|---|
| D1: nuhil hierarchy marked verified + eligible | Confirmed | 4,540 unions, 495 upazilas, 64 districts `verified=true, production_eligible=true` |
| D2: API ignores `production_eligible` | Confirmed | Only selected in `geo.sql.ts`, never filtered |
| D3–D6: master v3.0 arithmetic, registry and validator problems | Confirmed | See `docs/data/DATA_RECONCILIATION.md` |
| D7: Unicode mix | Confirmed | Precomposed and decomposed ড়/য় in the seed |
| D8: junk names | Confirmed | 5 names |
| D9: Wikipedia mirror links | Confirmed | 3 sources |
| C1: no lockfile, unfrozen CI install | Confirmed | |
| C2–C4: emergency page, fetch timeouts, route-handler errors and caching | Confirmed | |
| C5–C6: weak search fallback, no circuit breaker | Confirmed | `rajsahi` returned 0 areas |
| C7: no helmet, rate limiting, problem details, CSP | Confirmed | |
| C8–C10: seq-scan area filter, latitude-band nearby, eligibility default true | Confirmed | |
| C11: dark-mode contrast | Confirmed | 2.6:1 |
| C12–C21: smaller API/web issues | Confirmed | |
| Mockup issues | Not code | Recorded in the plan audit; the mockups are not shipped |

## Not found in the repository

The repository has no admin app, mobile/Flutter app, auth, PWA files, i18n or Redis usage. Those are new work, not migrations of existing code.
