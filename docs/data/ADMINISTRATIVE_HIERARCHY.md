# Administrative hierarchy

One self-referencing table, `admin_areas`, holds every level:

```
country → division → district → upazila ──→ union
                               ↘ city_corporation → ward (planned)
                     upazila → pourashava → ward (planned)
```

| Level | Rows | Sourced | Id range | Source |
|---|---|---|---|---|
| country | 1 | 1 | 1 | — |
| division | 8 | 8 | 10001–10008 | nuhil + BBS geocodes; population citypopulation.de (BBS 2022 adjusted) |
| district | 64 | 64 | 20001–20064 | nuhil; population citypopulation.de; boundary polygons (simplified) in PostGIS |
| upazila | 495 | 10 | 30001–30495 | nuhil (494) + Shayestaganj (Wikipedia) |
| union | 4,538 | 0 | 40001–44541 (gaps where duplicates were removed) | nuhil (+ Brahmandura, Wikipedia) |
| city_corporation | 13 | 13 | 50001–50013 | Wikipedia; Bogura from The Financial Express (May 2026) |
| pourashava | 14 | 0 | 60001–60014 | Rajshahi only, unverified |

- **URLs** are `admin_areas.path`, e.g. `/rajshahi/rajshahi/paba`. Paths are unique, and moving an area in the admin rewrites the paths of its whole subtree.
- **Search keys**: `name_key` is a generated Banglish key (`elaka_latin_key`, the twin of `latinKey` in `packages/shared`), indexed with trigrams.
- **Geometry**: `boundary` (MultiPolygon) and `centroid` are PostGIS `geography` columns. Districts have boundaries, so `/v1/geo/locate` resolves points to districts today.
- **Re-parenting**: `PATCH /v1/admin/areas/:id {parent_id, reason}` checks that the level fits (e.g. a union under an upazila), prevents cycles, respects the editor's geographic scope and is written to the audit log.

## Thanas, mouzas and villages (BBS Census 2022, Nov 2026)

`pipelines/localities.py` adds three levels from the Community Report table C-01 already in
`data/sources/bbs_census_2022*/raw/c01_*.csv`. It follows the census geocode; it never forces a unit into a tree the
census does not give it:

```
union / ward → mouza → village or mahalla        (C-01 nests every village code inside a mouza code)
city_corporation → thana                          (metropolitan police thana)
ward ⇢ thana                                      (admin_area_links, relation 'thana': a city ward can lie in two thanas)
```

| Level | Rows | Id range | Notes |
|---|---|---|---|
| thana | 105 | 80001– | city thanas only; thanas outside cities are police stations (places), not areas |
| mouza | 60,292 | 1000001– | a mouza split across unions or wards appears once per part, with a note; population is the part's |
| village | 104,882 | 2000001– | mahallas in city corporations and pourashavas carry a note |

- Names are English as BBS prints them. No Bangla source yet, so `name_bn` is empty (the site shows the English name and
  says so); nothing is transliterated. No coordinates or boundaries: the census publishes none for these levels.
- Evidence `official` (BBS), population `enumerated`.
- 448 census rows have no parent in the seed and are left out, listed in `data/seed/qa/localities_unplaced.csv`. They are
  cantonments, which the seed does not hold, and pourashava wards in Jhenaidah, where the census table repeats the
  pourashava code in the ward column.
- Places are filed by division, district, upazila, union and city corporation only. Ward, pourashava, thana, mouza and
  village pages show their nearest such area's places (`place_scope` in the area response).
