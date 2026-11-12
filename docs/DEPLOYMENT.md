# Deployment

Production deployment has **not** been performed from this repository yet. The chosen setup is **Cloudflare + Render** (below). The generic procedure after it applies to any host.

## Cloudflare + Render (production setup)

| Part | Where | Address |
|---|---|---|
| Public website (`apps/web`) | Cloudflare Workers (OpenNext) | https://elaka360.abusufyan.online |
| Admin (`apps/admin`) | Cloudflare Workers (OpenNext) | https://elaka360-admin.abusufyan.online |
| API (`apps/api`) | Render web service (Docker, `apps/api/Dockerfile`) | https://elaka360-api.abusufyan.online |
| Database | Render PostgreSQL 16 (PostGIS, no public access) | internal |

Hostnames use one level under `abusufyan.online` because Cloudflare's free certificate covers `*.abusufyan.online` only (`admin.elaka360.abusufyan.online` would need a paid certificate).

### How a release works

Pushing to `main` runs **CI** (`.github/workflows/ci.yml`). When CI passes, **Deploy** (`.github/workflows/deploy.yml`) runs:

1. **API.** It calls Render's deploy hook for that exact commit. Render builds the image, runs `scripts/db-migrate.sh` as the pre-deploy step (new migrations only, never drops data), then switches traffic. The job waits until `/health` reports the released commit.
2. **Website and admin.** They are built against the live API, then deployed with `opennextjs-cloudflare deploy`, which also fills the website's page cache. Cloudflare creates the DNS records and certificates for the custom domains. A smoke test checks `/emergency` and `/login`.

A part whose secrets are missing is skipped with a notice, so the setup can be done in stages. You can also start Deploy by hand (Actions → Deploy → Run workflow).

### One-time setup

**1. Render (API + database)**
1. Sign in at render.com and connect your GitHub account. Choose **New → Blueprint**, pick this repository, and apply `render.yaml`. This creates `elaka360-api` and `elaka360-db` in Singapore.
2. When asked for values:
   - `EDGE_SHARED_SECRET`: generate one with `openssl rand -base64 48` and keep it for step 3.
   - `SMS_PROVIDER`: leave empty. Phone sign-in returns 503 until an SMS gateway is integrated, but browsing works.
3. After the first deploy succeeds, open **elaka360-api → Shell** and run `bash scripts/db-seed-once.sh`. It loads the reference data once and refuses if the database already has data.
4. **elaka360-api → Settings → Custom Domains** lists `elaka360-api.abusufyan.online`. In Cloudflare DNS add a **CNAME** `elaka360-api` → `<service>.onrender.com`, set to **DNS only** (grey cloud), so Render can issue its certificate.
5. Copy the **Deploy Hook** URL from **elaka360-api → Settings**. It is a secret.

**2. Cloudflare**
1. Enable **R2** (dashboard → R2). The free tier is enough, but Cloudflare asks for a payment method. It stores the website's page cache.
2. Create an API token (My Profile → API Tokens → Create custom token) with these permissions:
   - Account: **Workers Scripts – Edit**, **Workers R2 Storage – Edit**, **Account Settings – Read**.
   - Zone `abusufyan.online`: **Workers Routes – Edit**, **DNS – Edit**, **Zone – Read**.
3. Note the **Account ID**, shown on the dashboard's right-hand side.

**3. GitHub (repository → Settings → Secrets and variables → Actions)**
- `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`: from step 2.
- `RENDER_DEPLOY_HOOK_URL`: from step 1.5.
- `EDGE_SHARED_SECRET`: the same value as in Render.

Optional: create the environment **production** (Settings → Environments) with required reviewers, so every release waits for an approval.

**4. First release.** Merge this branch into `main`. The Deploy workflow only runs from the default branch.

### Visitor IPs and rate limits

On Workers, every API call comes from Cloudflare's addresses. The website and admin therefore send the visitor's IP (from `CF-Connecting-IP`) in `X-Edge-Client-IP`, together with `EDGE_SHARED_SECRET`. The API trusts that IP only when the secret matches (`apps/api/src/common/edge-ip.ts`), so per-visitor limits work and direct callers cannot forge an IP. Without the secret, all visitors share Cloudflare's IPs and hit the sign-in limits together.

### Costs (approximate, Nov 2026)

| Part | Cost |
|---|---|
| Render web service `0.5c-512mb` (paid, needed for the pre-deploy migration step) | about $7/month |
| Render Postgres `0.1c-256mb` | about $6/month |
| Cloudflare Workers, R2 and Durable Objects free tiers | $0 at low traffic |

### Not set up yet

- **SMS gateway:** needed for sign-in and the admin. Until it exists, the first super admin cannot sign in.
- **Typesense:** search uses PostgreSQL. To add it, set `TYPESENSE_URL` and `TYPESENSE_API_KEY` on Render and run `search:reindex` from the Render Shell.
- **Error tracking:** none is configured.

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
