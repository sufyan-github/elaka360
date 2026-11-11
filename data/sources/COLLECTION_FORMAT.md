# Collected-source format

Every external dataset lives in its own folder under `data/sources/<source_key_lowercase>/` and is merged into the
seed by `pipelines/import_collected.py`. Nothing in these folders is published directly. Each row gets an evidence
level from its source's tier (see `docs/data/DATA_TRUST_POLICY.md`).

## Folder contents

| File | Required | What |
|---|---|---|
| `SOURCE.json` | yes | Provenance manifest (below) |
| `fetch.py` | yes | Re-runnable script that downloads and normalises the data (stdlib + `requests` only; polite: identify as `Elaka360-data-pipeline (research; contact via repository)`, ≥ 1 s between requests to the same host, honour robots.txt, no login, no CAPTCHA, no paywall) |
| `raw/` | if small | Raw downloads, **filtered to Rajshahi Division**, each file < 20 MB, total < 50 MB. Bigger raws are not committed: `fetch.py` must be able to rebuild them |
| `areas.csv` | when the source has admin units | Normalised admin units (columns below) |
| `boundaries.geojson` | when the source has polygons | Normalised boundaries (properties below) |
| `places.csv` | when the source has points of interest | Normalised places (columns below) |
| `facts.csv` | other figures | One fact per row (population, area, ward count …) |
| `REPORT.md` | yes | What was collected, counts, gaps, conflicts with other sources, licence notes |

## `SOURCE.json`

```json
{
  "key": "OSM_RAJ_2026",                       // UPPER_SNAKE, unique
  "name": "OpenStreetMap contributors — Rajshahi Division extract",
  "organization": "OpenStreetMap Foundation",
  "source_type": "community_dataset",          // government_portal | gazette | census | census_aggregator | encyclopedia | news | institution_website | community_dataset | humanitarian_dataset
  "trust_level": 1,                             // 5 gazette/LGD · 4 government portal/BBS · 3 reliable secondary · 2 project · 1 community
  "urls": ["https://…"],
  "accessed": "2026-11-12",
  "publication_date": null,
  "license": "ODbL-1.0",                        // exact licence id or null if none stated
  "license_url": "https://…",
  "attribution": "© OpenStreetMap contributors",
  "files": {"places.csv": "<sha256>", "raw/…": "<sha256>"},
  "notes": "…"
}
```

## `areas.csv`

`level, name_en, name_bn, parent_level, parent_name_en, parent_name_bn, district_en, upazila_en, code, code_scheme, website, lat, lon, source_key, source_url, notes`

- `level`: division | district | upazila | city_corporation | pourashava | union | ward | thana | mouza | village
- `code` + `code_scheme`: e.g. `BD50815025` + `HDX_PCODE`, or `50-81-15-25` + `BBS_GEOCODE_2011`
- Names exactly as the source spells them (Bangla NFC-normalised). Do not "correct" spellings; note doubts in `notes`.

## `boundaries.geojson`

FeatureCollection, EPSG:4326, coordinates rounded to 5 decimals, simplified so the file stays < 15 MB.
Properties: `level, name_en, name_bn, code, code_scheme, parent_code, district_en, upazila_en, source_key`.

## `places.csv`

`source_key, source_id, name_bn, name_en, category_key, lat, lon, address, district_en, upazila_en, phone, website, email, opening_hours, operator, ownership, extra_json, source_url, notes`

- `category_key`: a key from `data/seed/taxonomy/categories.csv` (e.g. `health.hospital`, `education.secondary_school`); use the top-level key if no sub-key fits; leave the row out if nothing fits.
- `source_id`: stable id in the source (e.g. `node/123456`, registry code).
- `phone` / `email`: **only** institutional contacts as published by the institution or government. Never personal numbers of private individuals.
- `extra_json`: other useful attributes as compact JSON (e.g. `{"beds": 50, "eiin": "123456"}`).

## `facts.csv`

`entity_level, entity_name_en, district_en, upazila_en, code, fact, value, unit, basis, year, source_key, source_url, notes`

e.g. `union, Harian, Rajshahi, Paba, , population, 31245, persons, enumerated, 2022, BBS_CENSUS_2022, https://…, `

## Rules

- No invented values. Missing stays empty; doubts go in `notes`.
- Every row carries `source_key` and, where possible, a `source_url` that a person can open to check it.
- Search-result pages, AI answers and unattributed blogs are not sources.
- Copyrighted text (descriptions, articles) is not copied; facts (names, codes, counts, coordinates) are.
