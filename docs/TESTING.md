# Testing

| Layer | Command | Needs |
|---|---|---|
| Seed pipeline unit tests | `python3 -m unittest pipelines/test_pipeline.py` | Python 3.11+ |
| Seed validation | `python3 pipelines/validate_seed.py` | Generated seed |
| Lint | `pnpm lint && pnpm lint:root` | |
| Unit (TS) | `pnpm test` | |
| SQL | `python3 scripts/check_sql.py` | Seeded DB |
| API integration | `node --test scripts/integration-api.test.mjs` | Running API with `SMS_PROVIDER=dev`, `OTP_RATE_PER_MIN≥100`; seeded DB (creates test users) |
| Smoke | `node scripts/smoke-api.mjs`, `node scripts/smoke-web.mjs` | Running API / web |
| End to end | `pnpm e2e` (Playwright, Pixel 7 + desktop Chrome) | Running API (`SMS_PROVIDER=dev`) and web; `pnpm exec playwright install chromium` once |

CI (`.github/workflows/ci.yml`) runs all of these on every pull request against PostGIS and Typesense services.
