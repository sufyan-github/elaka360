# Environment variables

## API (`apps/api`)

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `postgres://elaka360:elaka360@localhost:5432/elaka360` | PostgreSQL 16 + PostGIS + pg_trgm |
| `API_PORT` | 4000 | |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated: web and admin origins |
| `AUTH_JWT_SECRET` | random per process (dev only) | **Required in production**, at least 32 characters; the API refuses to start without it |
| `AUTH_ACCESS_TTL_S` / `AUTH_REFRESH_TTL_S` | 900 / 2592000 | Access token 15 min, refresh 30 days |
| `SMS_PROVIDER` | unset | Unset: OTP requests return 503. `dev`: the code is returned in the response; refused when `NODE_ENV=production` |
| `OTP_RATE_PER_MIN` | 5 | Per-IP OTP requests per minute. Raise only in tests |
| `OTP_PER_PHONE_15M` | 3 | Codes per phone number per 15 minutes. Raise only in tests |
| `STAFF_REQUIRE_2FA` | `true` when `NODE_ENV=production`, else `false` | Staff permissions need a session that passed TOTP two-factor authentication |
| `AUTH_TOTP_KEY` | derived from `AUTH_JWT_SECRET` | Key (≥ 32 chars) for encrypting TOTP secrets at rest. **Set it in production** so rotating the JWT secret does not lock staff out |
| `AUTH_ROTATION_GRACE_S` | 30 | Seconds the previous refresh token is accepted (parallel requests) |
| `THROTTLE_SCALE` | 1 | Multiplies every per-route rate limit. Tests only |
| `RATE_LIMIT_PER_MIN` | 240 | Global per-IP limit |
| `PUBLIC_INCLUDE_UNVERIFIED` | `true` | Unverified records are shown publicly with warnings (product decision). `false` = strict: only sourced records. Hotlines are sourced-only in both modes. See `docs/data/DATA_TRUST_POLICY.md` |
| `TYPESENSE_URL`, `TYPESENSE_API_KEY` | unset | Search falls back to Postgres when unset or down |
| `SEARCH_COOLDOWN_MS` | 30000 | Circuit-breaker pause after a Typesense failure |
| `DB_POOL_MAX`, `DB_STATEMENT_TIMEOUT_MS` | 10, 8000 | |
| `TRUST_PROXY_HOPS` | 1 | For the client IP behind a load balancer |
| `ACCESS_LOG` | on | `off` disables the JSON access log |
| `APP_VERSION` | `dev` | Shown in `/health` |

## Web (`apps/web`) and admin (`apps/admin`)

| Variable | Default | Notes |
|---|---|---|
| `API_URL` | `http://localhost:4000` | Server-side only; the browser never calls the API directly |
| `API_TIMEOUT_MS` | 5000 | Server-side fetch timeout |
| `NEXT_PUBLIC_SITE_URL` | `http://localhost:3000` | Canonical origin, also accepted by the CSRF Origin check |
| `NEXT_PUBLIC_MAP_STYLE_URL` | OpenFreeMap positron | Basemap style; its origin is added to the CSP |
