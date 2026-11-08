# Elaka360 — notes for Claude / contributors

- Monorepo: pnpm workspaces + Turborepo. Apps: `apps/web` (Next.js 15 App Router, Tailwind v4), `apps/api` (NestJS 11, `pg`).
  Packages: `@elaka360/shared` (types + Bangla formatting, compiled to CommonJS in `dist/`), `@elaka360/ui` (CSS tokens).
- UI language is Bangla first. Store ASCII digits; format with `formatNumber/formatCompact/formatDate/toBnDigits`
  from `@elaka360/shared`. Never hard-code national counts — read `/v1/stats/national`.
- Area URLs are `admin_areas.path` (e.g. `/rajshahi/rajshahi/paba`); place URLs are `/p/<slug>`.
- API SQL lives in `*.sql.ts` constants (or `export const X_SQL` in controllers). When you add one, add sample params to
  `scripts/check_sql.py` so CI executes it against the seed.
- Schema changes: add a new numbered file in `db/migrations/` (never edit an applied one) and mirror types in
  `packages/shared/src/types.ts`.
- Seed data is generated: edit `pipelines/refdata.py` or `data/sources/`, then `pnpm seed:build`. CI fails if the
  committed seed differs from a fresh build.
- Facts need sources. Anything unverified gets `verified=false` / `production_eligible=false`.
- Before pushing: `pnpm build && pnpm typecheck && pnpm test`; with a DB: `pnpm db:reset && python3 scripts/check_sql.py`.
