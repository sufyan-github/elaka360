# Collected data — Rajshahi Division (12 Nov 2026)

Rajshahi Division is the first area filled from official sources. Each source sits in its own folder under
`data/sources/<key>/` with a provenance manifest, a re-runnable `fetch.py` and a `REPORT.md`
(format: [COLLECTION_FORMAT.md](../../data/sources/COLLECTION_FORMAT.md)). `pipelines/import_collected.py` merges them
into the seed. Each record gets its evidence level from its source's trust level
([DATA_TRUST_POLICY.md](DATA_TRUST_POLICY.md)), and every change is logged in `data/seed/qa/collected_changes.csv`.

## Administrative areas

| Level | Records | Official evidence | With boundary |
|---|---|---|---|
| District | 8 | 8 | 8 |
| Upazila | 67 | 67 | 67 |
| Union | 566 | 566 | 540 |
| Pourashava | 62 | 62 | 14 |
| Ward | 618 | 618 | 28 |
| City corporation | 2 | 1 (Rajshahi) | 1 |

- **Counts and populations:** BBS Census 2022, checked against the district, upazila and union portals and LGD.
- **Spellings:** Bangla spellings come from the official portals. A spelling is changed only when the two names are clearly the same; 12 doubtful pairs are logged as `name_bn_review` and left unchanged.
- **Boundaries:** geoBoundaries ADM4 and the HDX COD-AB, matched to BBS geocodes through `hdx_cod_ab_bgd/crosswalk.csv`.
- **Resolved conflicts:**
  - Bagha has 7 unions (চকরাজাপুর added).
  - Sirajganj has 83 unions and Pabna 74.
  - Gabtali has 12 unions (সুখানপুকুর added).
  - Rajshahi District has 14 pourashavas.
  - Rajshahi City Corporation's population is 553,288.
- **Still open:** each remaining conflict is listed in [UNRESOLVED_CONFLICTS.md](UNRESOLVED_CONFLICTS.md), and the evidence is summarised in [OFFICIAL_RAJSHAHI_SUMMARY.md](../../data/sources/OFFICIAL_RAJSHAHI_SUMMARY.md).

## Places (points of interest)

21,113 places: 8 curated pilot places plus 21,268 rows from 19 government registers and portals. 148 rows were merged into a record from another source, and 15 were skipped (12 Fire Service staff posts and 3 rows outside the taxonomy).

| Category | Places | With coordinates | Main sources |
|---|---|---|---|
| Education | 14,413 | 5 | DPE IPEMIS (primary schools), BANBEIS (EIIN), UGC, DGME |
| Health | 5,056 | 3,726 | DGHS HRIS facility registry |
| Government offices | 883 | 15 | Divisional, district and upazila portals, Bangladesh Post |
| Tourism | 401 | 129 | Department of Archaeology protected monuments, portal tourist spots |
| Emergency | 185 | 0 | Police (RMP, district police, Police HQ 2020 list), Fire Service |
| Finance | 100 | 0 | District portal bank lists |
| Religious | 41 | 5 | Department of Archaeology, portals |
| Transport | 23 | 1 | Bangladesh Railway, CAAB, BRTC, district portals |
| Agriculture | 11 | 0 | Portals |

### How places are placed in areas

- **Area assignment:** places are matched to upazilas by name. Rajshahi Metropolitan Police thanas go to the city corporation, or to Paba for the rural thanas. 20,700 places resolve to an upazila or city corporation.
- **Coordinates:** a point is accepted only if it falls inside the stated district; 252 were dropped. Accepted points then give the union.
- **Union from text:** the union can also come from the DPE union field or a union parishad's name. 9,747 places have a union.

### Merging duplicates

- **When records merge:** two records merge only if they come from different sources, are in the same district and compatible category, and are in the same upazila when both state one.
- **How names are compared:** only the part of the name that tells places apart is compared. Type words ("Govt. Primary School", "থানা") and area names are ignored.
- **One-per-upazila places:** a police station or upazila health complex named only by type merges only within its own upazila.
- **What the merge keeps:** the merged record keeps every source in `attributes._sources`.

### Contacts and evidence

- **Contacts:** only institutional contacts are kept. Staff Gmail addresses from the DGHS registry are dropped, and so are Facebook, YouTube and blog links. 2,856 places have a phone number.
- **Evidence:** every collected place has `official` evidence. `verification_status` stays `unverified` until staff review it.
- **Pilot places:** when a pilot place was confirmed by a register, its evidence source is the register, but its details are still credited to their original source. The place page shows both, for example "Source: UGC register · Details from: Wikipedia".

### Web addresses

A place with an English name gets a slug from that name plus its upazila. A place with only a Bangla name gets a romanised slug (`collected.romanize_bn`). Slugs and public ids are deterministic, so a rebuild gives the same URLs.

## Not done yet

- **OpenStreetMap:** the extract (shops, mosques, markets, roads) was still downloading when this was written. When it is added it will come in as `community` evidence under the ODbL licence.
- **Coordinates:** most schools and offices have none. The registers do not publish them.
- **Phone numbers:** the Police HQ numbers are from a 2020 list and may be out of date. The notes on each record say so.
- **Other divisions:** they still rely on the community dataset.
