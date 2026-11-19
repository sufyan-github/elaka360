# Implementation roadmap

Each phase ends at a gate (measurable), not a date.

| Phase | Scope | Gate | State |
|---|---|---|---|
| 0 | Baseline audit | Baseline documented | Done (`REPOSITORY_AUDIT.md`) |
| 1 | Data trust, eligibility enforcement | No unsupported verification; public endpoints filtered | Done |
| 2 | Master reconciliation | Every seed/master difference tracked and validated in CI | Done for Rajshahi Division; conflicts open |
| 3 | Backend completion | Integration tests pass | Done (except media, Google sign-in, Open Data) |
| 4 | Admin | Moderation + verification usable end to end | See final report |
| 5 | Public website | Core journeys pass in Playwright (mobile + desktop) | Done |
| 6 | PWA/offline | Installable; emergency works offline | Done (no offline packs) |
| 7 | UX/a11y | Lighthouse a11y 100 on key pages; no overflow at phone width | Done for audited pages |
| 8 | Security/reliability | Headers, limits, timeouts, failure tests | Done |
| 9 | QA/CI | All CI gates green | Local runs green; first CI run pending push |
| 10 | Docs | Docs match implementation | Done |
| 11 | Production | Release gates in `docs/DEPLOYMENT.md` | **Blocked**: SMS gateway, hosting, official data |

## Next work, in order

1. Official evidence: import the LGD union list and BBS geocodes, and verify Rajshahi Division first. Use the admin verification centre and close the 16 tracked conflicts.
2. SMS gateway contract plus a provider adapter in `apps/api/src/auth/sms.ts` (staff 2FA is done).
3. Upazila/union boundaries (BBS/HDX ADM3–4) so `/geo/locate` resolves below district level.
4. Media uploads (R2 + EXIF stripping).
5. Release-pinned Open Data bulk files (the keyed live API is done).
