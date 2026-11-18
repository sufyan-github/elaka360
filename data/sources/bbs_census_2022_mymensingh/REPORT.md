# BBS Population and Housing Census 2022 — Mymensingh Division

Source key `BBS_CENSUS_2022_MYMENSINGH` · census · trust level 4 · accessed 2026-11-18 · collected by
`python3 -I data/sources/bbs_census_2022/fetch.py --division mymensingh --cache <scratch>` · division `mymensingh` · kind `bbs_census`.

## What was obtained

Same page as the earlier runs (<https://bbs.gov.bd/pages/static-pages/6922e073933eb65569e27220>), resolved on
2026-11-18 (exact URLs: `raw/resolved_urls.json`):

| Document | Used for |
|---|---|
| Community Report Excel per district (4), sheet **C_01** (Table C-01) | every geocoded unit down to village/mahalla, households, population by sex, rural/urban |
| District Report PDFs (4) | Key Findings (PDF pages 25–27): unit counts, area, density; area narrative on PDF page 39 (not in Sherpur) |
| Union Statistics PDF (national, June 2025), Table D01, PDF page 66 | district unit counts, households, population |

Downloads ≈ 120 MB (not committed; `fetch.py --division mymensingh` rebuilds; `--offline` rebuilds from `raw/`).
Committed: `raw/c01_mymensingh_division.csv` (1.1 MB, 15,132 C-01 rows incl. 8,323 village/mahalla rows, as printed),
`raw/district_report_key_findings.txt`, `raw/union_statistics_D01.txt`, `raw/resolved_urls.json`. areas.csv 1.8 MB
(6,029 rows), facts.csv 1.4 MB (3,747 rows); same fact set, `basis` values and code scheme (`BBS_GEOCODE_2022`,
division prefix 45) as the earlier runs. No Bangla names in the source.

fetch.py changes for this run:
- Mymensingh district table (order of the Community Report list on the BBS page; labels as printed there; geocodes
  checked against the first C-01 row of each Excel): Mymensingh 61, Jamalpur 39, Sherpur 89, Netrokona 72 (page label
  NETRAKONA; output name Netrokona as in the seed).
- `c01_rows` also accepts a sheet named `C_01` (all four Mymensingh workbooks use it), checked by the "Table C-01" title
  like the existing `C01` fallback. The C-01 headers needed no other change (the extra SL/DSN/... header row above the
  table is skipped by the existing header search).

Earlier divisions unchanged:
- Rajshahi, full run with no `--division` (live downloads) into a scratch `--out`: areas.csv, facts.csv and all four raw
  files byte-identical with the committed folder (including `raw/resolved_urls.json`).
- Rangpur/Dhaka/Chattogram/Khulna/Barishal/Sylhet: URL resolution on the current listing page identical to each
  committed `raw/resolved_urls.json`; `--offline` rebuilds from the committed raw/ byte-identical (Rajshahi too).
- No difference came from a live source or a seed change.

## Coverage

| District | Geocode | Population (enum.) | Households (C-01) | Upazilas | City corp. / thanas | Paurashavas | Unions | Paura wards | City wards | Mauza rows |
|---|---|---:|---:|---:|---|---:|---:|---:|---:|---:|
| Mymensingh | 45-61 | 5,899,005 | 1,460,534 | 13 | 1 / 1 | 10 | 145 | 90 | 33 | 2,338 |
| Jamalpur | 45-39 | 2,499,738 | 651,954 | 7 | – | 8 | 68 | 75 | – | 876 |
| Sherpur | 45-89 | 1,501,853 | 396,060 | 5 | – | 4 | 52 | 36 | – | 499 |
| Netrokona (printed "Netrakona") | 45-72 | 2,324,853 | 548,351 | 10 | – | 5 | 86 | 45 | – | 1,617 |
| **Division** | 45 | **12,225,449** | | **35** | **1 / 1** | **27** | **351** | **246** | **33** | **5,330** |

Division totals agree with the D01 division row for upazilas (35), paurashavas (27), paura wards (246), unions (351) and
population; D01 prints 34 city wards (see below), 5,035 mauzas, 1,111 mahallas and 7,212 villages.
- Tarakanda upazila (45-61-88, 10 unions, population 337,308, no paurashava) is in the 2022 frame; Fulpur (45-61-81)
  has 10 unions.
- Hazrabari Paurashava (45-39-61-26, Melandaha) is the second paurashava of Melandaha upazila.

**Non-union units in the Union/Ward column:**
- **Cantonment** (45-61-40-52-998), a ward-type row inside the city corporation's metro thana (population 3,916). Kept at
  level `cantonment` with the existing note; not counted as a city ward or union.
- No 997 (forest) row. No cantonment, forest or haor row in any upazila's union list.
- 24 unions have "Char" in the name (e.g. Char Algi, Char Ishwardia, Char Nilakkhia, Char Betagair, Bagarchar, Merurchar,
  Char Putimari, Char Pakkhimari, Char Sherpur). All are printed "... Union" with Rural/Urban rows: ordinary union
  parishads, kept at level `union`.
- No unit above mauza level is marked "(Part)". 412 mauza rows are "(Part)".

## Mymensingh City Corporation (geocode 45-61-40, seed 50012 in Mymensingh district 20062)

- Population 577,000 (C-01: 293,582 male, 283,345 female, 73 hijra). Households 135,366. The seed has 471,858 (`WIKI_CC`, census).
- **1 metro thana:** Mymensingh Sadar Thana (45-61-40-52), the same population as the city corporation.
- **33 wards (Ward No. 01–33)**, one row each, none split. `ward_count` = 33, the same as the Key Findings "City Ward"
  figure (33). D01 prints 34: the 33 wards plus the Cantonment row.
- 332 mahallas and 32 distinct mauza codes, no unions inside the city corporation. City-ward mauzas include Akua (Part),
  Kewatkhali, Bayra Bhaluka (Part) and Mymensingh Town (Part).
- Thana code 52 repeats the Mymensingh Sadar upazila code (45-61-52, 11 unions). Always use the full geocode (45-61-40-…).

## Printed vs derived counts (conflicts inside BBS)

- **Upazilas, paurashavas, paura wards, villages, mahallas, population:** Key Findings, D01 and the derived counts agree in every district.
- **Unions:** they agree in Jamalpur, Sherpur and Netrokona. In Mymensingh the Key Findings print 144, while D01 and
  C-01 have 145. The difference is not explained by a non-union row; it is left as printed.
- **City wards:** Key Findings 33 = C-01; D01 34 (includes the Cantonment row).
- **Mauzas:** Key Findings = D01 in every district: Mymensingh 2,167, Jamalpur 819, Sherpur 456, Netrokona 1,593
  (incl. depopulated mauzas). The derived distinct counts differ: 2,226 / 816 / 468 / 1,587. Mauzas split between the city
  corporation and an upazila are counted in both, so derived can be higher. Use the printed totals.
- **Households:** D01 includes floating households, so it is slightly higher than C-01.
- **Area:** Key Findings = English narrative for Mymensingh (4,363.48), Jamalpur (2,115.16) and Netrokona (2,794.28).
  Sherpur (1,364.67) has no narrative figure.
- **Names:** C-01 and D01 print the district "Netrakona"; the Key Findings table prints "Netrokona". C-01 district facts keep
  the printed name in `entity_name_en`; `district_en` is Netrokona throughout.

## Basis and seed comparison

Population is the final enumerated count incl. floating population, not PEC-adjusted. Division enumerated total (D01):
12,225,449. The seed district `population_2022` (`CITYPOP_ADJ`, "adjusted") equals BBS enumerated × 1.03370 for every
district (seed division 12,637,472). It is a proportional figure computed by the aggregator, not a BBS figure.

| District | Seed (CITYPOP_ADJ) | BBS enumerated | Seed area km² | BBS area km² (Key Findings) |
|---|---:|---:|---:|---:|
| Mymensingh | 6,097,814 | 5,899,005 | 4357.7 | 4363.48 |
| Jamalpur | 2,583,984 | 2,499,738 | 2070.1 | 2115.16 |
| Sherpur | 1,552,469 | 1,501,853 | 1328.6 | 1364.67 |
| Netrokona | 2,403,205 | 2,324,853 | 2809.4 | 2794.28 |

The seed areas are computed from polygons. The seed has no Mymensingh Division pourashavas (BBS 27).

## Upazilas and unions vs the seed (BBS 35 / 351 vs seed 35 / 352)

Name-matched with the HDX matcher (direction words not used: the division has no direction twins). Upazila pairs were
checked against the seed's Bangla names. Spelling-only differences are not listed.
- **All 35 upazilas pair correctly:** 27 exact (incl. Tarakanda তারাকান্দা), 1 banglish (Fulpur = Phulpur ফুলপুর) and 7
  skeleton/medium: Bakshiganj = Bokshiganj (বকশীগঞ্জ), Dewanganj = Dewangonj (দেওয়ানগঞ্জ), Melandaha = Melandah (মেলান্দহ),
  Nakla = Nokla (নকলা), Sreebardi = Sreebordi (শ্রীবরদী), Mohanganj = Mohongonj (মোহনগঞ্জ), Netrakona Sadar = Netrokona Sadar.
- **Unions:** 341 matched (245 high, 92 medium, 4 low).

| Upazila (BBS) | BBS | Seed | Difference |
|---|---:|---:|---|
| Mymensingh Sadar | 11 | 13 | seed Aqua (আকুয়া) and Boyra (বয়ড়া) have no BBS union; their mauzas (Akua, Kewatkhali, Bayra Bhaluka) appear in city wards |
| Nandail | 13 | 12 | BBS Bir Betagair and Char Betagair vs one seed Batagoir (বেতাগৈর); not paired (which one is the seed's is not stated) |

Pairs the matcher does not make, but which are the same union by the seed's Bangla name:
- Chhandhara ~ Sondhara (ছনধরা, Phulpur)
- Nanni ~ Nonni (নন্নী), Poragaon ~ Puraga (পোড়াগাও), Ramchandrakura Mandaliapara ~ Ramchondrokura (রামচন্দ্রকুড়া) (Nalitabari)
- Dhala ~ Dhola (ধলা), Lachhmanpur ~ Losmonpur (লছমনপুর) (Sherpur Sadar)
- Duaz ~ Duoj (দুওজ, Atpara)
- Roailbari ~ Roailbari Amtala (রোয়াইলবাড়ী আমতলা, Kendua)

Low-confidence matcher pairs to review (all agree with the seed's Bangla name): Rajai~Rajoi (রাজৈ), Shunai~Shunoi (শুনই),
Changaon~Chandgaw (চানগাঁও), Mauganti~Mougati (মৌগাতি).

These are census-frame counts as of mid-2022; later gazette changes are not reflected.

## Licence
No licence is stated on bbs.gov.bd. Facts only (names, codes, counts) are copied; attribution "Bangladesh Bureau of
Statistics, Population and Housing Census 2022".
