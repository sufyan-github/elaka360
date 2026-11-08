# Elaka360 data — seed v0.1 (9 Nov 2026)

Regenerate with `pnpm seed:build` (runs `pipelines/build_seed.py` over `data/sources/`).

Real seed data for the Elaka360 app, built from public sources. It is stack-agnostic: CSV, JSON and GeoJSON files, plus PostgreSQL schema and seed files that load cleanly on PostgreSQL 16.

## What's inside

| Folder | Contents |
|---|---|
| `seed/geo/admin_areas.csv / .json` | One table for the whole hierarchy: country → 8 divisions → 64 districts → 495 upazilas → 4,541 unions, plus 13 city corporations and 14 Rajshahi pourashavas. Each row has Bangla and English names, a URL path, the official website, and `verified` / `production_eligible` flags. |
| `seed/geo/{divisions,districts,upazilas,unions,city_corporations}.csv` | The same rows split by level. |
| `seed/geo/hierarchy_tree.json` | A nested tree for the Explore screens. |
| `seed/geo/districts.geojson` | District boundaries for the map. Each feature carries `district_id`, `division_id`, `name_bn` and `name_en`. |
| `seed/taxonomy/categories.*` | 11 top-level categories and 84 subcategories, taken from the mockups, with Bangla/English labels, icon names and colours. |
| `seed/reference/emergency_hotlines.csv` | National short codes, each with a verified flag and source. |
| `seed/reference/data_sources.csv` | Every source used, with its URL. |
| `seed/pilot_rajshahi/places.*` | 8 Rajshahi places (RU, RUET, RMCH, Puthia Rajbari, Varendra Museum and others). The verified ones include coordinates and facts. |
| `seed/pilot_rajshahi/mockup_demo_fixtures_NOT_REAL.json` | Names from the mockups that couldn't be verified (Durbin Cafe and others). These are UI fixtures only; don't import them. |
| `seed/qa/mockup_vs_verified.csv` | 26 figures in the mockups that are wrong or out of date, with the correct value and its source. |
| `seed/qa/known_gaps.csv` | What is still missing and how to fill it. |
| `db/migrations/*.sql`, `db/seed/seed.sql` | Postgres schema (20 tables) and inserts for everything above. |

## Load into Postgres

```
createdb elaka360
psql -d elaka360 -f db/migrations/0001_init.sql
psql -d elaka360 -f db/seed/seed.sql
```

## ID scheme (stable)

| Range | Level |
|---|---|
| `1` | country |
| `10001–10008` | divisions |
| `20001–20064` | districts |
| `30001–30495` | upazilas |
| `40001–44541` | unions |
| `50001–50013` | city corporations |
| `60001+` | pourashavas |

The upstream ids are kept in `source_ref`.

## Rules followed

- Mockup numbers were treated as placeholders and never copied as facts.
- Anything not checked against a source has `verified=false`, and new additions also carry `production_eligible=false`. This matches the v2.8 release rule in the admin mockup.
- Population figures are BBS Census 2022 **adjusted** at division and district level (they sum to 169,828,911). The Rajshahi upazila figures are **enumerated**. Pick one basis for the app.
- District areas are computed from the boundary polygons and are approximate: Rajshahi's polygon gives 2,443 km² against the official 2,425.37 km². Only Rajshahi District uses the official figure.

## Licence

The hierarchy and boundaries derive from nuhil/bangladesh-geocode (MIT, licence file included in `geo/`). Census figures come from BBS via citypopulation.de. Other facts link to their sources in `reference/data_sources.csv`.
