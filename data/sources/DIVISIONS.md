# Collecting a division

Rajshahi Division was collected first (Nov 2026). The other divisions reuse the same collectors, one division at a time.
Read [COLLECTION_FORMAT.md](COLLECTION_FORMAT.md) first: file formats, politeness and licence rules all still apply.

## Divisions

| Division | Code | BBS geocode | Seed id | Districts (seed ids) |
|---|---|---|---|---|
| Rajshahi | `raj` | 50 | 10002 | 20012–20019 |
| Rangpur | `rang` | 55 | 10007 | Panchagarh 20053, Dinajpur 20054, Lalmonirhat 20055, Nilphamari 20056, Gaibandha 20057, Thakurgaon 20058, Rangpur 20059, Kurigram 20060 |
| Dhaka | `dhk` | 30 | 10006 | 20040–20052 |
| Chattogram | `ctg` | 20 | 10001 | 20001–20011 |
| Khulna | `khl` | 40 | 10003 | 20020–20029 |
| Barishal | `bar` | 10 | 10004 | 20030–20035 |
| Sylhet | `syl` | 60 | 10005 | 20036–20039 |
| Mymensingh | `mym` | 45 | 10008 | 20061–20064 |

City corporations in the seed:

| City corporation | Seed id | District |
|---|---|---|
| Dhaka North | 50001 | Dhaka |
| Dhaka South | 50002 | Dhaka |
| Chattogram | 50003 | Chattogram |
| Khulna | 50004 | Khulna |
| Rajshahi | 50005 | Rajshahi |
| Sylhet | 50006 | Sylhet |
| Barishal | 50007 | Barishal |
| Rangpur | 50008 | Rangpur |
| Cumilla | 50009 | Cumilla |
| Narayanganj | 50010 | Narayanganj |
| Gazipur | 50011 | Gazipur |
| Mymensingh | 50012 | Mymensingh |
| Bogura | 50013 | Bogura |

## Collectors take a division

Every `fetch.py` accepts:

```
python3 fetch.py --division <rajshahi|rangpur|dhaka|chattogram|khulna|barishal|sylhet|mymensingh> [--out DIR]
```

- **Default:** `--division rajshahi` with the collector's own folder as output. Running it with no arguments must behave exactly as before, and the Rajshahi outputs are never rewritten by another division's run.
- **Other divisions** write to their own folder (naming below), with their own `SOURCE.json` and `REPORT.md`.

## Folder and key naming for a new division

Folder names, applied to the Rajshahi folder name:
- `_raj_` → `_<code>_`, for example `dghs_hris_facilities_raj_2026` → `dghs_hris_facilities_rang_2026`.
- `rajshahi_` → `<division>_`, for example `rajshahi_upazila_portals` → `rangpur_upazila_portals`.
- A national source without a division in its name gets a suffix: `bbs_census_2022` → `bbs_census_2022_rangpur`.
- Rajshahi-only city sources become named city sources:
  - `rcc` → `rangpur_city_corporation`
  - `rmp` → `rangpur_metro_police`
  - `rmp_thanas_2026` → `rangpur_metro_police_thanas_2026`

`SOURCE.json` keys follow the same rule in upper case:
- `DGHS_HRIS_FACILITIES_RAJ_2026` → `DGHS_HRIS_FACILITIES_RANG_2026`.
- `RAJSHAHI_…` → `RANGPUR_…`.
- `RAJDIV_…` → `RANGDIV_…`.
- National keys get a suffix: `BBS_CENSUS_2022` → `BBS_CENSUS_2022_RANGPUR`.

Every `SOURCE.json`, including the existing Rajshahi ones, also carries:
- `"division"`: `"rajshahi"`, `"rangpur"`, …
- `"kind"`: one of the values below. The importer finds a division's sources by these two fields, not by key.

| kind | Rajshahi folder |
|---|---|
| `bbs_census` | bbs_census_2022 |
| `hdx_cod_ab` | hdx_cod_ab_bgd |
| `geoboundaries_adm4` | geoboundaries_bgd_adm4 |
| `dghs_geocodes` | dghs_bd_geocodes |
| `lgd` | lgd |
| `district_portal_main` | rajshahi_district_portal (the division's head district) |
| `district_portals` | division_district_portals (the other districts) |
| `upazila_portals` | rajshahi_upazila_portals |
| `union_portals` | rajshahi_union_portals |
| `divisional_portal` | rajshahi_divisional_portal |
| `city_corporation` | rcc |
| `metro_police` | rmp |
| `metro_police_thanas` | rmp_thanas_2026 |
| `district_police` | rajshahi_police_2026 |
| `range_police` | raj_range_police_portals_2026 |
| `police_hq_2020` | bd_police_contacts_2020 |
| `fscd` | fscd_stations_raj_2026 |
| `dghs_hris` | dghs_hris_facilities_raj_2026 |
| `banbeis` | banbeis_inst_raj_2026 |
| `dpe_ipemis` | dpe_ipemis_primary_raj_2026 |
| `ugc` | ugc_universities_raj_2026 |
| `dgme` | dgme_medical_colleges_raj_2026 |
| `doa_monuments` | doa_protected_monuments_raj_2026 |
| `bdpost` | bdpost_postcodes_raj_2026 |
| `railway` | bd_railway_raj_2026 |
| `caab` | caab_airports_raj_2026 |
| `brtc` | brtc_depots_raj_2026 |
| `bb_banks` | bb_scheduled_banks_raj_2026 |
| `district_banks` | district_portal_banks_raj_2026 |
| `district_transport` | district_portals_transport_raj_2026 |
| `tourist_spots` | portal_tourist_spots_raj_2026 |
| `portal_offices` | rajshahi_portal_offices_2026 |
| `osm` | osm_rajshahi_division |

## Done for a division when

1. Every collector that applies has run, and its folder has `SOURCE.json` (with `files` checksums), the data files and `REPORT.md`. Some sources don't exist for a division (no city corporation, no airport): write that in the report rather than leaving files empty.
2. `python3 pipelines/build_seed.py && python3 pipelines/validate_seed.py` passes.
3. The seed changes are committed, then the D1 export and sync run. The sync stays within the daily D1 write budget shared with the account's other databases.
