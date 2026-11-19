# Deployment

**Live since 12 Nov 2026** on Cloudflare's free plan: https://elaka360.abusufyan.online. It serves the public site:
areas, places, search, the live map and emergency numbers. Sign-in, contributions and the admin need an SMS gateway and
the full API, so they are not deployed yet (see "Later" below).

## Cloudflare + Turso (free plans)

| Part | Where | Address |
|---|---|---|
| Website (`apps/web`) | Worker `elaka360-web` (OpenNext); page cache in R2 `elaka360-web-cache`, Durable Object revalidation queue | https://elaka360.abusufyan.online |
| Public API (`apps/edge-api`) | Worker `elaka360-api`, reading a **Turso** database (libSQL/SQLite, region Mumbai `aws-ap-south-1`); reached by the website through a service binding | https://elaka360-api.abusufyan.online |
| Map boundaries and pin tiles | static files in the website (`/data/map`) | — |

The edge database moved from D1 to Turso in Nov 2026: with OpenStreetMap, Overture, Wikidata and organisations' branch
lists the data is about 2.7 GB (measured as SQLite) — one Turso database on the free plan (5 GB), against D1's
500 MB per database and 100,000 rows written per day.

### How it fits the free plans

- **The API is a snapshot of the reference API.**
  - The NestJS API on PostgreSQL stays the source of truth. `apps/api/src/cli/export-edge.ts` runs its own services against a database loaded with the seed (and the Overture layer) and writes every public response: area pages, place pages, ordered lists, stats and the search tables.
  - The Worker only looks these up, so each request uses little CPU (the Workers free limit is 10 ms) and few rows (Turso free: 500 million reads a month).
  - In CI, `scripts/edge-parity.py` compares 39 endpoints of the Worker with the NestJS API and fails on any difference; search, which is ranked by a different engine, gets its own checks.
- **Turso writes: 10 million rows a month.** `scripts/turso-sync.mjs` writes only rows whose content hash changed and deletes rows that disappeared; `--budget` stops a run and the next run continues. The first full load is about 1.6 million rows; a release that changes nothing writes nothing.
- **Search runs in the edge database** (SQLite FTS5 tables `search_areas`, `search_places`): word prefixes in Bangla and English plus the Banglish key; the rowid encodes the result order, so a query reads only the rows it returns. The website calls it through `/api/search` and `/api/suggest`.
- **The map loads static pin tiles** (0.05°, `/data/map/tiles/<x>_<y>.json`, listed in `tiles.json`) for the visible area from zoom 12, so no file comes near the 25 MiB asset limit (the densest tile, central Dhaka, is about 8.5 MB). It refreshes them every 5 minutes.
- **Pages are cached in R2.** Home, area and place pages are refreshed every 5 minutes. `/c/<category>` renders on every visit and is the page most at risk of Cloudflare's "Error 1102" (CPU limit). Watch the Worker's metrics.

### Release (GitHub Actions, `.github/workflows/deploy.yml`)

After CI passes on `main`, or when started by hand:
1. The Overture layer is rebuilt from its pinned release (its place files are not committed), a throwaway PostGIS database in the job is loaded with the seed and the layer, and `export-edge` runs.
2. `turso-sync` writes the changed rows to Turso (budget 9 million per run).
3. The API Worker is deployed with the `TURSO_DATABASE_URL` / `TURSO_AUTH_TOKEN` secrets. The job waits until `/health` reports the commit.
4. The website is built against the live API and deployed (the R2 page cache is filled), then smoke-tested.

### One-time setup

- **Turso** (you, once): create a free account at turso.tech, then a database in the Mumbai region and a token, e.g. with the Turso CLI:
  `turso db create elaka360 --location aws-ap-south-1`, `turso db show elaka360 --url` (the `libsql://…` URL) and
  `turso db tokens create elaka360` (the token). Keep the token secret.
- **Cloudflare** (done on 12 Nov 2026): R2 bucket `elaka360-web-cache`, both Workers with custom domains, and the `EDGE_SHARED_SECRET` Worker secret on both Workers. The old D1 database `elaka360` is no longer used and can be deleted.
- **GitHub secrets, needed for automatic releases:**
  - `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` (above).
  - `CLOUDFLARE_ACCOUNT_ID` = `d89998f5da60c9ff528edc0f2a7fca59`.
  - `CLOUDFLARE_API_TOKEN`: a custom token (My Profile → API Tokens) with these permissions:
    - Account: **Workers Scripts – Edit**, **Workers R2 Storage – Edit**, **Account Settings – Read**.
    - Zone `abusufyan.online`: **Workers Routes – Edit**, **Zone – Read**, **DNS – Edit**.
  - Optional `EDGE_SHARED_SECRET`: the Workers already have one. If you set this, it replaces it on both Workers.
- **Manual release from a signed-in machine** (`npx wrangler login`):
  - Optional, to include Overture: `python3 data/sources/overture_places_raj_2026/fetch.py --all --release 2026-10-21.0 && pnpm seed:build`.
  - Run `pnpm db:reset`, then `pnpm --filter @elaka360/api build && pnpm edge:export`.
  - Run `TURSO_DATABASE_URL=libsql://… TURSO_AUTH_TOKEN=… pnpm edge:sync`.
  - In `apps/edge-api`: `npx wrangler secret put TURSO_DATABASE_URL`, `npx wrangler secret put TURSO_AUTH_TOKEN`, then `npx wrangler deploy`.
  - In `apps/web`, run `API_URL=https://elaka360-api.abusufyan.online NEXT_PUBLIC_SITE_URL=https://elaka360.abusufyan.online pnpm cf:build && pnpm cf:deploy`.
- **Local edge stack:** `pnpm edge:db` (libSQL server on port 8080), `pnpm edge:export`, `pnpm edge:sync`, then
  `pnpm --filter @elaka360/edge-api dev` (port 8789).

### Later: the full API (accounts, contributions, admin)

These need the NestJS API with PostgreSQL and an SMS gateway. `apps/api/Dockerfile` and `render.yaml` prepare a Render deployment (about $13/month).
When that exists, point the website's sign-in and account routes at it.

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
- First load of reference data on an empty production database: run `db-migrate.sh`, then `bash scripts/db-seed-once.sh` (it runs `psql -f db/seed/seed.sql`, which includes the per-division parts) **once**. The seed is an initial load, not an upsert.
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
