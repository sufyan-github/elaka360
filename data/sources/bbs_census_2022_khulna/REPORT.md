# BBS Population and Housing Census 2022 — Khulna Division

Source key `BBS_CENSUS_2022_KHULNA` · census · trust level 4 · accessed 2026-11-18 · collected by
`python3 -I data/sources/bbs_census_2022/fetch.py --division khulna` · division `khulna` · kind `bbs_census`.

## What was obtained

Same page as the earlier runs (<https://bbs.gov.bd/pages/static-pages/6922e073933eb65569e27220>), resolved on
2026-11-18 (exact URLs: `raw/resolved_urls.json`):

| Document | Used for |
|---|---|
| Community Report Excel per district (10), sheet **C-01** | every geocoded unit down to village/mahalla, households, population by sex, rural/urban |
| Community Report PDF, Jhenaidah only (720 pages, created 26 May 2025), "List of Geocodes of Jhenaidah District" (PDF page 25) | union and ward codes missing from Jhenaidah's Excel (below) |
| District Report PDFs (10; PDF creation dates 23 May – 12 Jun 2024, 276–452 pages) | Key Findings: unit counts, area, density |
| Union Statistics PDF (national, June 2025), Table D01, PDF pages 65–66 | district unit counts, households, population |

Downloads ≈ 265 MB (not committed; `fetch.py --division khulna` rebuilds; `--offline` rebuilds from `raw/`).
Committed: `raw/c01_khulna_division.csv` (1.5 MB, 20,756 C-01 rows incl. 11,228 village/mahalla rows, as printed),
`raw/community_report_geocodes.txt`, `raw/district_report_key_findings.txt`, `raw/union_statistics_D01.txt`,
`raw/resolved_urls.json`. areas.csv 2.5 MB (8,223 rows), facts.csv 2.4 MB (6,136 rows); same fact set, `basis` values
and code scheme (`BBS_GEOCODE_2022`, division prefix 40) as the earlier runs. No Bangla names in the source.

fetch.py changes for this run:
- Khulna district table (labels and order as on the BBS page; geocodes checked against the first C-01 row of each Excel).
- **Jhenaidah union/ward codes** (`GEOCODE_LIST_DISTRICTS`): Jhenaidah's Excel leaves the Union/Ward code empty on all
  67 union rows and repeats the paurashava code there on every ward row (and on the paurashava row itself). The C-01
  table in the Community Report PDF is printed the same way. Without a fix, the unions were read as upazilas and the 54
  wards as one ward per paurashava. The fix:
  - For listed districts only, the collector downloads the Community Report PDF and keeps its "List of Geocodes" page
    as `raw/community_report_geocodes.txt`.
  - `build()` fills in the union and ward codes from that BBS-printed list, matching by upazila code and name (case
    ignored: Excel "Sbk Union", list "SBK Union"). Mauza and village rows take the code of the union/ward row above them.
  - Every filled row says so in `notes`. The C-01 CSV in `raw/` stays as printed. A name missing from the list stops the
    run; nothing is guessed.
- **Sundarbans Reserve Forest units** are now level `reserve_forest`, not `union`: four rows printed in the Union/Ward
  column with code 997 (see Coverage). Each upazila with one gets a derived `reserve_forest_unit_count`.
- Neither change touches the earlier divisions: none has a code-997 row, and none has a district in
  `GEOCODE_LIST_DISTRICTS`.

Rajshahi/Rangpur/Dhaka/Chattogram outputs are unchanged:
- URL resolution, new code on the current listing page vs the committed `raw/resolved_urls.json`: identical for all four.
- `--offline` rebuilds of areas.csv/facts.csv from the committed raw/ into a scratch folder: byte-identical for all four.
- The Excel and PDF extraction code is unchanged, so the earlier raw files were not downloaded again.
- A second full Khulna run into a scratch folder gave byte-identical files.

## Coverage

| District | Geocode | Population (enum.) | Households | Upazilas | City corp. / thanas | Paurashavas | Unions | Paura wards | City ward rows | Mauza rows |
|---|---|---:|---:|---:|---|---:|---:|---:|---:|---:|
| Khulna | 40-47 | 2,613,385 | 670,567 | 9 | 1 / 5 | 2 | 68 | 18 | 32 | 777 |
| Bagerhat | 40-01 | 1,613,076 | 408,663 | 9 | – | 3 | 75 | 27 | – | 741 |
| Satkhira | 40-87 | 2,196,582 | 566,657 | 7 | – | 2 | 78 | 18 | – | 937 |
| Jhenaidah | 40-44 | 2,005,849 | 519,208 | 6 | – | 6 | 67 | 54 | – | 980 |
| Chuadanga | 40-18 | 1,234,054 | 326,647 | 4 | – | 4 | 41 | 36 | – | 406 |
| Magura | 40-55 | 1,033,115 | 254,139 | 4 | – | 1 | 36 | 9 | – | 541 |
| Kushtia | 40-50 | 2,149,692 | 565,096 | 6 | – | 5 | 66 | 57 | – | 741 |
| Meherpur | 40-57 | 705,356 | 195,322 | 3 | – | 2 | 20 | 18 | – | 205 |
| Jashore | 40-41 | 3,076,144 | 797,803 | 8 | – | 8 | 93 | 72 | – | 1,368 |
| Narail | 40-65 | 788,671 | 195,636 | 3 | – | 3 | 39 | 27 | – | 460 |
| **Division** | 40 | **17,415,924** | | **59** | **1 / 5** | **36** | **583** | **336** | **32** | **7,156** |

Division totals agree with the D01 division row: 1 city corporation, 5 metro thanas, 32 city ward rows, 59 upazilas,
36 paurashavas, 336 paura wards, 583 unions. D01 also prints 6,925 mauzas, 1,673 mahallas and 9,555 villages.

**Not union parishads** (in areas.csv with their own level and population facts):
- Cantonment: Jashore Cantonment (40-41-47-998, under Jashore Sadar; enumerated population 18,869), level `cantonment`.
- Sundarbans Reserve Forest, code 997, level `reserve_forest`. Each has one mauza row:
  - Nalian Range (40-47-17-997, Dacope; population 14).
  - Chandpai Range (40-01-58-997, Mongla; 139).
  - Sundarban (Reserve Forest) (40-01-77-997, Sharankhola; 159; its mauza is "Sharankhola Range").
  - Satkhira Range (40-87-86-997, Shyamnagar; 120).

## Khulna City Corporation (geocode 40-47-33, seed 50004)

- Population 719,557 (C-01). The seed has 718,735 (`WIKI_CC`, census).
- **5 thanas:** Daulatpur (6 wards), Khalishpur (9), Khan Jahan Ali (1), Khulna Sadar (9), Sonadanga (7).
- **31 wards (Ward No. 01–31), printed as 32 ward rows:** Ward 02 is split between Daulatpur and Khan Jahan Ali thanas
  ("Ward No. 02 (Part)" under both). The `ward_count` facts count distinct ward codes (31).
- 184 mahallas and 19 mauza codes; no unions inside the city corporation.
- City-ward codes 001–031 repeat the paura-ward numbers. Always use the full geocode (40-47-33-…).

## Printed vs derived counts (conflicts inside BBS)

- **Upazilas, paurashavas, paura wards, villages, population:** Key Findings, D01 and derived counts agree in every
  district.
- **Unions:** the Key Findings count the non-union units, D01 and the derived counts do not:
  - Khulna 69 vs 68 (Nalian Range).
  - Bagerhat 77 vs 75 (Chandpai Range, Sundarban (Reserve Forest)).
  - Jashore 94 vs 93 (Jashore Cantonment).
  - Satkhira 78 in all three (Satkhira Range is not counted).
- **Khulna district, Key Findings:**
  - "City Ward" is printed as **26** for 2022 (31 in the 2011 column). C-01 has 31 ward numbers and D01 prints 32 (ward
    rows). Kept as printed, with this conflict noted here.
  - "Mahalla" is printed as **184**: that is Khulna City Corporation's mahalla count. D01 and the derived count give 210,
    which includes 26 paurashava mahallas. Kept as printed.
- **Mauzas:** Key Findings = D01 in every district. The derived counts differ: split mauzas are counted per upazila, and
  depopulated mauzas have no row. Use the printed totals: Khulna 771, Bagerhat 722, Satkhira 953, Jhenaidah 946,
  Chuadanga 383, Magura 527, Kushtia 699, Meherpur 202, Jashore 1,286, Narail 436.
- **Households:** D01 includes floating households, so it is slightly higher than C-01.

## Basis and seed comparison

Population is the final enumerated count incl. floating population, not PEC-adjusted. Division enumerated total (D01):
17,415,924. The seed district `population_2022` (`CITYPOP_ADJ`, "adjusted") equals BBS enumerated × 1.02281 for every
district (seed division 17,813,219). It is a proportional figure computed by the aggregator, not a BBS figure.

| District | Seed (CITYPOP_ADJ) | BBS enumerated | Seed area km² | BBS area km² (Key Findings) |
|---|---:|---:|---:|---:|
| Jashore | 3,146,317 | 3,076,144 | 2591.2 | 2606.94 |
| Satkhira | 2,246,691 | 2,196,582 | 3404.9 | 3817.29 |
| Meherpur | 721,447 | 705,356 | 724.2 | 741.62 |
| Narail | 806,662 | 788,671 | 998.0 | 967.99 |
| Chuadanga | 1,262,205 | 1,234,054 | 1168.6 | 1174.10 |
| Kushtia | 2,198,731 | 2,149,692 | 1618.5 | 1608.78 |
| Magura | 1,056,683 | 1,033,115 | 1051.4 | 1039.10 |
| Khulna | 2,673,002 | 2,613,385 | 3641.5 | 4394.45 |
| Bagerhat | 1,649,874 | 1,613,076 | 3660.7 | 3959.11 |
| Jhenaidah | 2,051,607 | 2,005,849 | 1961.0 | 1964.77 |

The seed areas are computed from polygons. The BBS figures include rivers and the Sundarbans/coastal areas, hence the
gaps for Khulna, Satkhira and Bagerhat. The seed has no Khulna Division pourashavas (BBS 36).

## Unions vs the seed (BBS 583 vs seed 574), per upazila where the count differs

Name-matched with the HDX matcher (direction words read as North/South/East/West); spelling-only differences are not
listed. Upazila pairs the matcher cannot make were checked against the seed's Bangla names: Dacope = seed Dakop (দাকোপ;
9 unions on both sides), Paikgachha = seed Paikgasa (পাইকগাছা).

| Upazila | BBS | Seed | Difference |
|---|---:|---:|---|
| Keshabpur | 11 | 9 | Hasanpur, Satbaria only in BBS |
| Meherpur Sadar | 7 | 5 | Baradi, Shyampur only in BBS |
| Chuadanga Sadar | 10 | 7 | Garaitupi, Makhaldanga, Nehalpur only in BBS |
| Damurhuda | 8 | 7 | Natudaha only in BBS |
| Jibannagar | 8 | 6 | Kdk, Manoharpur only in BBS |
| Kushtia Sadar | 13 | 14 | Kanchanpur only in BBS; Barkhada, Mazampur only in the seed |

Pairs the matcher does not make, but which are probably the same union spelled differently: Diara ~ Dearamodel (Jashore
Sadar), Maghi ~ Moghi (Magura Sadar), Lata ~ Lota (Paikgachha), Tilak Swalpa Bahirdia ~ Tsb (Rupsa).

These are census-frame counts as of mid-2022; later gazette changes are not reflected.

## Licence
No licence is stated on bbs.gov.bd. Facts only (names, codes, counts) are copied; attribution "Bangladesh Bureau of
Statistics, Population and Housing Census 2022".
