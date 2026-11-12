# Deployment

**Live since 12 Nov 2026** on Cloudflare's free plan: https://elaka360.abusufyan.online. It serves the public site:
areas, places, search, the live map and emergency numbers. Sign-in, contributions and the admin need an SMS gateway and
the full API, so they are not deployed yet (see "Later" below).

## Cloudflare (free plan)

| Part | Where | Address |
|---|---|---|
| Website (`apps/web`) | Worker `elaka360-web` (OpenNext); page cache in R2 `elaka360-web-cache`, Durable Object revalidation queue | https://elaka360.abusufyan.online |
| Public API (`apps/edge-api`) | Worker `elaka360-api` on D1 `elaka360` (APAC); reached by the website through a service binding | https://elaka360-api.abusufyan.online |
| Map boundaries + pins, search index | static files in the website (`/data/map`, `/data/search`) | — |

### How it fits the free plan

- **The API is a snapshot of the reference API.**
  - The NestJS API on PostgreSQL stays the source of truth. `apps/api/src/cli/export-edge.ts` runs its own services against a database loaded with the seed and writes every public response: area pages, place pages, ordered lists and stats.
  - The Worker only looks these up, so each request uses little CPU (the free limit is 10 ms) and few D1 rows (5 million reads a day).
  - In CI, `scripts/edge-parity.py` compares 39 endpoints of the Worker with the NestJS API and fails on any difference.
- **D1 writes are limited to 100,000 rows a day, shared by every database in the account.**
  - `scripts/d1-sync.mjs` writes only rows whose content hash changed, and it stops at `--budget`; running it again continues.
  - A full load is about 74,000 rows, so the first load was split over two days. It loads curated places first, then places on the map, then the rest.
- **Search runs in the browser** (`apps/web/lib/browser-search.ts`) over a static index of about 560 KB compressed, loaded on the first search. A server-side substring search would use up D1's read allowance.
- **The map loads static files.** It refreshes them every 5 minutes, which picks up new releases.
- **Pages are cached in R2.** Home, area and place pages are refreshed every 5 minutes. `/c/<category>` renders on every visit and is the page most at risk of Cloudflare's "Error 1102" (CPU limit). Watch the Worker's metrics.

### Release (GitHub Actions, `.github/workflows/deploy.yml`)

After CI passes on `main`, or when started by hand:
1. A throwaway PostGIS database in the job is loaded with the seed, and `export-edge` runs.
2. The changed D1 rows are synced. Exit code 10 means the write budget was reached: the run warns, and the next run finishes the load.
3. The API Worker is deployed. The job waits until `/health` reports the commit.
4. The website is built against the live API and deployed (the R2 page cache is filled), then smoke-tested.

### One-time setup (already done on 12 Nov 2026, except the GitHub secrets)

- D1 `elaka360` (id in `apps/edge-api/wrangler.jsonc`), R2 bucket `elaka360-web-cache`, both Workers with custom domains, and the `EDGE_SHARED_SECRET` Worker secret on both Workers.
- **GitHub secrets, needed for automatic releases:**
  - `CLOUDFLARE_ACCOUNT_ID` = `d89998f5da60c9ff528edc0f2a7fca59`.
  - `CLOUDFLARE_API_TOKEN`: a custom token (My Profile → API Tokens) with these permissions:
    - Account: **Workers Scripts – Edit**, **D1 – Edit**, **Workers R2 Storage – Edit**, **Account Settings – Read**.
    - Zone `abusufyan.online`: **Workers Routes – Edit**, **Zone – Read**, **DNS – Edit**.
  - Optional `EDGE_SHARED_SECRET`: the Workers already have one. If you set this, it replaces it on both Workers.
- **Manual release from a signed-in machine** (`npx wrangler login`):
  - Run `pnpm db:reset`, then `pnpm --filter @elaka360/api build && pnpm edge:export`.
  - Run `node scripts/d1-sync.mjs --remote`.
  - In `apps/edge-api`, run `npx wrangler deploy`.
  - In `apps/web`, run `API_URL=https://elaka360-api.abusufyan.online NEXT_PUBLIC_SITE_URL=https://elaka360.abusufyan.online pnpm cf:build && pnpm cf:deploy`.

### Later: the full API (accounts, contributions, admin)

These need the NestJS API with PostgreSQL and an SMS gateway. `apps/api/Dockerfile` and `render.yaml` prepare a Render deployment (about $13/month).
When that exists, point the website's sign-in and account routes at it, or move those parts to D1 as well.

## Components

| Component | Build | Run | Health |
|---|---|---|---|
| API | `pnpm --filter @elaka360/api build` | `node apps/api/dist/main.js` (≥ 2 replicas) | `GET /health` (DB latency, search engine + circuit state) |
| Web | `pnpm --filter @elaka360/web build` | `pnpm --filter @elaka360/web start` | `GET /emergency` (static, works without the API) |
| Admin | `pnpm --filter @elaka360/admin build` | `pnpm --filter @elaka360/admin start` (port 3001), behind staff-only network rules if possible | `GET /login` |
| Database | PostgreSQL 16 with PostGIS 3.4 and pg_trgm | managed, PITR backups | |
| Search | Typesense 27 (optional) | `pnpm --filter @elaka360/api search:reindex` after data changes | |

## Database

- **Never run `scripts/db-reset.sh` outside development.** It drops the schema, and it refuses non-local hosts and `NODE_ENV=production`.
- Apply migrations with `DATABASE_URL=… bash scripts/db-migrate.sh`. It records each file's SHA-256 in `schema_migrations`, skips applied files and aborts if an applied file changed.
- First load of reference data on an empty production database: run `db-migrate.sh`, then `psql -f db/seed/seed.sql` **once**. The seed is an initial load, not an upsert.
- Backups: daily snapshots + point-in-time recovery on the managed database. To restore, restore the snapshot to a new instance, run `db-migrate.sh` (a no-op if current), point `DATABASE_URL` at it and run `search:reindex`.
- Grant the first super admin after they have signed in once: `node apps/api/dist/cli/grant-role.js +8801XXXXXXXXX super_admin`.

## Release checklist (release gates)

1. `python3 pipelines/validate_seed.py` passes: no unsupported verification.
2. CI green: lint, typecheck, unit, SQL check, integration, smoke, Playwright.
3. `AUTH_JWT_SECRET` and `AUTH_TOTP_KEY` set; `SMS_PROVIDER` is a real gateway (not `dev`); `NODE_ENV=production` (which turns on `STAFF_REQUIRE_2FA`); `THROTTLE_SCALE`, `OTP_*` limits left at their defaults.
4. `CORS_ORIGINS` lists only the web and admin origins; HTTPS everywhere.
5. `/emergency` loads with the API stopped.
6. Open conflicts in `docs/data/UNRESOLVED_CONFLICTS.md` remain unsourced (shown only with warnings).
7. Every staff account has enrolled an authenticator; the first super admin enrols on first admin sign-in.
