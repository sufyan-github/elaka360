# Administrative hierarchy

One self-referencing table, `admin_areas`, holds every level:

```
country → division → district → upazila ──→ union
                               ↘ city_corporation → ward (planned)
                     upazila → pourashava → ward (planned)
```

| Level | Rows | Public | Id range | Source |
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
