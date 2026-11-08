# Elaka360 — Every Place. Every Detail.

Bengali-first, mobile-first local-information platform for Bangladesh: the full admin hierarchy
(division → district → upazila → union, plus city corporations and pourashavas), institutions,
businesses, tourist spots and emergency services — from official sources and community contributions.

## Status

**Phase 0 (foundations) + the first Phase 1 screens.** Read-only public app over a real seed dataset:

| | |
|---|---|
| Data | 8 divisions · 64 districts · 495 upazilas · 4,541 unions · 13 city corporations · 95 categories · 10 hotlines · 8 verified Rajshahi pilot places |
| API | `apps/api` — NestJS REST `/v1`: areas, stats, categories, places, nearby, search, emergency numbers |
| Web | `apps/web` — Next.js PWA shell: Home, Explore, area pages (every level), place page, category list, search, Near me, Emergency |

## Repo layout

```
apps/web         Next.js (App Router) public app — Tailwind v4 + Elaka360 tokens
apps/api         NestJS modular monolith over PostgreSQL
packages/shared  domain types, Bangla number/date formatting (lakh/crore, ০-৯), search keys
packages/ui      design tokens (CSS variables + Tailwind theme)
db/migrations    SQL schema (20 tables)        db/seed/seed.sql   generated seed
data/sources     vendored upstream data (nuhil/bangladesh-geocode, MIT)
data/seed        generated CSV / JSON / GeoJSON + QA reports (see data/README.md)
pipelines        Python seed builder (reference data with sources in refdata.py)
scripts          db reset, SQL checker, API + web smoke tests
```

## Run locally

Requirements: Node 22+, pnpm 10, Docker (or any PostgreSQL 14+), Python 3.11+ (only to rebuild the seed).

```bash
cp .env.example .env
pnpm install
pnpm db:up                       # PostGIS in Docker on :5432
pnpm db:reset                    # schema + seed
pnpm --filter @elaka360/shared build
pnpm dev                         # API on :4000, web on :3000
```

Open http://localhost:3000 and try `/rajshahi/rajshahi`, `/p/university-of-rajshahi`, `/emergency`.

## Useful commands

| Command | What it does |
|---|---|
| `pnpm build` / `pnpm typecheck` / `pnpm test` | All workspaces via Turborepo |
| `pnpm seed:build` | Regenerate `data/seed` + `db/seed/seed.sql` from `data/sources` + `pipelines/refdata.py` |
| `pnpm db:reset` | Drop, migrate and seed the database at `$DATABASE_URL` |
| `python3 scripts/check_sql.py` | Execute every API SQL statement against the seeded DB |
| `node scripts/smoke-api.mjs` / `node scripts/smoke-web.mjs` | End-to-end checks against running servers |

CI (`.github/workflows/ci.yml`) runs all of the above on every push, against a real PostGIS service.

## Data rules

- Mockup numbers are placeholders, never facts. Every record carries a source, `verified` and `production_eligible`.
- See `data/seed/qa/mockup_vs_verified.csv` (26 corrections) and `data/seed/qa/known_gaps.csv`.

## Roadmap

0. Foundations ✅ · 1. Rajshahi pilot (read-only, search, map, emergency, admin geo/places) · 2. Community
(contribute, moderation, profiles, saved/offline) · 3. National scale (import pipeline, dedup, releases, Open Data API).
