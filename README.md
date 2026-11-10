# Elaka360 — Every Place. Every Detail.

Bengali-first, mobile-first local-information platform for Bangladesh: the admin hierarchy (division → district →
upazila → union, plus city corporations and pourashavas), institutions, tourist spots and emergency services,
**always shown with the evidence behind it**: sourced records are marked as such, and everything else carries a "not verified" warning. See [docs/data/DATA_TRUST_POLICY.md](docs/data/DATA_TRUST_POLICY.md).

## Status (November 2026)

Rajshahi pilot. Public reads, accounts, contributions, moderation and an admin app are in place. Most of the
national hierarchy comes from a community dataset and is **shown with a "not verified" warning** until it is checked
against official sources:

| | Rows in database | Sourced (secondary evidence) |
|---|---|---|
| Divisions / districts | 8 / 64 | 8 / 64 (secondary sources) |
| Upazilas | 495 | 10 (Rajshahi's 9 + Shayestaganj) |
| Unions | 4,538 | 0 (community dataset, shown with warnings) |
| City corporations | 13 | 13 |
| Places | 8 | 5 |
| Hotlines | 10 | 7 (only these are shown) |

No record has official (Tier 1) evidence yet. The full feature status is in
[docs/implementation/FINAL_IMPLEMENTATION_REPORT.md](docs/implementation/FINAL_IMPLEMENTATION_REPORT.md).

## Repo layout

```
apps/web         Next.js 15 public PWA (Bangla UI, ISR pages, httpOnly-cookie sessions)
apps/admin       Next.js 15 staff app: dashboard, verification centre, areas, places, moderation, sources, audit, users
apps/api         NestJS 11 modular monolith over PostgreSQL 16 + PostGIS (raw parameterised SQL), OpenAPI at /docs
packages/shared  domain types, Bangla formatting (lakh/crore, ০-৯), labels, search keys
packages/ui      design tokens (light/dark, category colours) + Tailwind v4 theme
db/migrations    0001–0006, additive        db/seed/seed.sql   generated seed
data/sources     nuhil/bangladesh-geocode (MIT) + compact copy of Consolidated Master v3.0
data/seed        generated CSV/JSON/GeoJSON + QA reports      pipelines   seed builder, trust policy, reconciliation, validator
scripts          db reset/migrate, SQL checker, smoke + integration tests     tests/e2e   Playwright
docs             data policy, reconciliation, environment, deployment, testing, implementation reports
```

## Run locally

Requirements: Node 22+, pnpm 10, Docker (PostGIS), Python 3.11+.

```bash
cp .env.example .env
pnpm install --frozen-lockfile
pnpm db:up                       # PostGIS on :5432
pnpm db:reset                    # migrations + seed (development only)
pnpm build
SMS_PROVIDER=dev pnpm dev        # API :4000, web :3000, admin :3001 (dev: OTP codes shown on screen)
```

Make yourself an admin after signing in once:

```bash
DATABASE_URL=postgres://elaka360:elaka360@localhost:5432/elaka360 node apps/api/dist/cli/grant-role.js 01XXXXXXXXX super_admin
```

## Commands

| Command | What it does |
|---|---|
| `pnpm build` / `typecheck` / `test` / `lint` | All workspaces via Turborepo |
| `pnpm seed:build` | Regenerate `data/seed`, `db/seed/seed.sql`, generated docs |
| `python3 pipelines/validate_seed.py` | Trust-policy, duplicate, parent, junk-name and master-reconciliation checks |
| `pnpm db:reset` | **Dev only**: drop, migrate, seed (refuses non-local hosts) |
| `bash scripts/db-migrate.sh` | Apply pending migrations safely (staging/production) |
| `python3 scripts/check_sql.py` | Execute every API SQL statement against the seeded DB |
| `pnpm test:integration` / `pnpm e2e` | API integration tests / Playwright (servers running) |

More: [docs/ENVIRONMENT.md](docs/ENVIRONMENT.md) · [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) · [docs/TESTING.md](docs/TESTING.md).
