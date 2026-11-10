# Deployment

Production deployment has **not** been performed from this repository. This is the procedure the code supports.

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
