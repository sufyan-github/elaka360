# BBS Population and Housing Census 2022 — Dhaka Division

Source key `BBS_CENSUS_2022_DHAKA` · census · trust level 4 · accessed 2026-11-17 · collected by
`python3 -I data/sources/bbs_census_2022/fetch.py --division dhaka` · division `dhaka` · kind `bbs_census`.

## What was obtained

Same page as the Rajshahi/Rangpur runs (<https://bbs.gov.bd/pages/static-pages/6922e073933eb65569e27220>), resolved on
2026-11-17 (exact URLs: `raw/resolved_urls.json`):

| Document | Used for |
|---|---|
| Community Report Excel per district (13), sheet **C-01** | every geocoded unit down to village/mahalla, households, population by sex, rural/urban |
| District Report PDFs (13; PDF creation dates 21 May – 12 Jun 2024, 300–564 pages) | Key Findings: unit counts, area, density |
| Union Statistics PDF (national, June 2025), Table D01, PDF page 65 | district unit counts, households, population |

Downloads ≈ 340 MB (not committed; `fetch.py --division dhaka` rebuilds; `--offline` rebuilds from `raw/`). Committed:
`raw/c01_dhaka_division.csv` (2.8 MB, 37,764 C-01 rows incl. 21,819 village/mahalla rows),
`raw/district_report_key_findings.txt`, `raw/union_statistics_D01.txt`, `raw/resolved_urls.json`.
areas.csv 4.2 MB (13,967 rows), facts.csv 3.8 MB (10,398 rows); same fact set, `basis` values and code scheme
(`BBS_GEOCODE_2022`, division prefix 30) as the Rajshahi/Rangpur runs. No Bangla names in the source.

fetch.py changes for this run (Rajshahi/Rangpur outputs unchanged, checked by full online reruns): Dhaka district table;
upazila/thana names keyed by (city corporation, code), because Narayanganj City Corporation's Bandar and Narayanganj
Sadar thanas reuse the codes 06/58 of the Bandar and Narayanganj Sadar upazilas; Key Findings start also detected when
"01" and "Administrative Units" are on separate lines (Manikganj); label "City Corporation Ward" (Narayanganj).

## Coverage

| District | Geocode | Population (enum.) | Households | Upazilas | City corp. / thanas | Paurashavas | Unions | Paura wards | City ward rows | Mauza rows |
|---|---|---:|---:|---:|---|---:|---:|---:|---:|---:|
| Dhaka | 30-26 | 14,734,701 | 4,029,271 | 5 | 2 / 53 | 3 | 62 | 27 | 163 | 1,192 |
| Narayanganj | 30-67 | 3,909,138 | 1,022,792 | 5 | 1 / 2 | 5 | 39 | 45 | 27 | 737 |
| Gazipur | 30-33 | 5,263,450 | 1,579,198 | 5 | 1 / 8 | 3 | 39 | 27 | 61 | 821 |
| Manikganj | 30-56 | 1,558,025 | 393,341 | 7 | – | 2 | 65 | 18 | – | 1,211 |
| Narsingdi | 30-68 | 2,584,452 | 621,359 | 6 | – | 6 | 71 | 57 | – | 665 |
| Faridpur | 30-29 | 2,162,879 | 525,580 | 9 | – | 6 | 81 | 72 | – | 1,101 |
| Gopalganj | 30-35 | 1,295,057 | 308,646 | 5 | – | 4 | 67 | 42 | – | 669 |
| Rajbari | 30-82 | 1,189,818 | 295,017 | 5 | – | 3 | 42 | 27 | – | 775 |
| Shariatpur | 30-86 | 1,294,562 | 308,880 | 6 | – | 6 | 65 | 54 | – | 630 |
| Kishoreganj | 30-48 | 3,267,626 | 760,627 | 13 | – | 8 | 108 | 75 | – | 960 |
| Munshiganj | 30-59 | 1,625,416 | 399,444 | 6 | – | 2 | 68 | 18 | – | 607 |
| Madaripur | 30-54 | 1,293,027 | 313,203 | 5 | – | 4 | 60 | 36 | – | 572 |
| Tangail | 30-93 | 4,037,608 | 1,061,574 | 12 | – | 11 | 120 | 108 | – | 2,048 |
| **Division** | 30 | **44,215,759** | | **89** | **4 / 63** | **63** | **887** | **606** | **251** | **11,988** |

Cantonments (level `cantonment`, Union/Ward column, code 998, not union parishads): Savar Cantonment (30-26-72-998),
Gazipur Cantonment (30-33-30-998), Sheikh Russel Cantonment (30-86-94-998, Zajira).

## City corporations (kept apart by the city-corporation code in the geocode)

| City corporation | Geocode | Seed id | Population (C-01) | Seed (WIKI_CC) | Thanas | Wards | Ward rows | Mahallas | Mauzas listed |
|---|---|---|---:|---:|---:|---|---:|---:|---:|
| Dhaka South | 30-26-20 | 50002 | 4,305,063 | 4,299,345 | 25 | 75 (1–75) | 89 | 867 | 143 |
| Dhaka North | 30-26-25 | 50001 | 5,990,723 | 5,979,537 | 28 | 54 (1–54) + Ward No. 98 (Restricted Area, Cantonment Thana) | 74 | 687 | 167 |
| Gazipur | 30-33-33 | 50011 | 2,677,715 | 2,674,697 | 8 | 57 (1–57) | 61 | 424 | 204 |
| Narayanganj | 30-67-44 | 50010 | 967,951 | 967,724 | 2 | 27 (1–27) | 27 | 184 | 76 |

- Ward numbers repeat between city corporations (Dhaka South ward 1 ≠ Dhaka North ward 1). Always use the full geocode,
  e.g. `30-26-20-36-001` vs `30-26-25-…-001`.
- A ward split between thanas appears once per thana as "Ward No. N (Part)"; `ward_count` facts count distinct ward
  codes.
- Dhanmondi, Ramna and Shere Bangla Nagar thanas appear in both Dhaka South and Dhaka North (same thana code, separate
  rows and populations), so Dhaka district has 53 thana rows and 50 distinct thana codes.
- **Dhaka district's metro area:** C-01 has no unions inside Dhaka North/South. The metro is listed only as city
  corporation → metro thana → ward → mauza → mahalla. The 62 unions of Dhaka district are all in its 5 upazilas
  (Dhamrai, Dohar, Keraniganj, Nawabganj, Savar). Gazipur City Corporation has 8 metro thanas (Basan, Gachha, Kashimpur,
  Konabari, Pubail, Tongi Pashchim, Tongi Purba, Joydebpur); Narayanganj City Corporation has 2 (Bandar, Narayanganj
  Sadar).

## Printed vs derived counts (conflicts inside BBS)

- **Unions:** Key Findings, D01 and C-01 agree except Dhaka (Key Findings 63 vs 62) and Gazipur (40 vs 39). The
  difference is the cantonment (Savar, Gazipur). Shariatpur's Sheikh Russel Cantonment is counted in neither.
- **City wards:** Key Findings Dhaka 129 (= 75 + 54) vs D01 163; Gazipur 57 vs D01 61. D01 counts ward rows, with split
  wards counted once per thana. Narayanganj 27 in both.
- **Mahallas:** Narayanganj Key Findings prints City Mahalla 184 / Paura Mahalla 209 on two lines. The parser does not
  read this, so there is no Key Findings mahalla fact; D01 393 (= derived). The other districts agree.
- **Villages, paurashavas, upazilas, paura wards, population:** Key Findings, D01 and derived counts agree in every
  district.
- **Mauzas:** Key Findings = D01 everywhere; the derived counts are lower (mauzas split across upazilas are counted per
  upazila, and depopulated mauzas have no row). Use the printed totals.

  | District | KF / D01 | Derived | District | KF / D01 | Derived |
  |---|---:|---:|---|---:|---:|
  | Dhaka | 1,130 | 1,113 | Rajbari | 835 | 749 |
  | Narayanganj | 759 | 705 | Shariatpur | 616 | 583 |
  | Gazipur | 792 | 794 | Kishoreganj | 948 | 914 |
  | Manikganj | 1,314 | 1,192 | Munshiganj | 636 | 585 |
  | Narsingdi | 634 | 626 | Madaripur | 531 | 527 |
  | Faridpur | 1,035 | 1,009 | Tangail | 2,001 | 1,989 |
  | Gopalganj | 625 | 618 | | | |
- **Area:** Gopalganj Key Findings 1,468.74 km² vs the report's English narrative 1,489.92 km². Both are kept, with
  notes. Tangail density is printed with decimals (1187.56).
- **Households:** D01 includes floating households, so it is slightly higher than C-01.

## Basis and seed comparison

Population is the final enumerated count incl. floating population, not PEC-adjusted. Division enumerated total (D01):
44,215,759. The seed district `population_2022` (`CITYPOP_ADJ`, "adjusted") equals BBS enumerated × 1.03231 for every
district (seed division 45,644,586). It is a proportional figure computed by the aggregator, not a BBS figure, and was
not checked against a BBS adjusted figure.

| District | Seed (CITYPOP_ADJ) | BBS enumerated | Seed area km² | BBS area km² (Key Findings) |
|---|---:|---:|---:|---:|
| Dhaka | 15,210,851 | 14,734,701 | 1478.8 | 1463.60 |
| Narayanganj | 4,035,461 | 3,909,138 | 705.4 | 684.35 |
| Gazipur | 5,433,538 | 5,263,450 | 1821.4 | 1806.36 |
| Manikganj | 1,608,372 | 1,558,025 | 1377.4 | 1383.66 |
| Narsingdi | 2,667,968 | 2,584,452 | 1170.6 | 1150.14 |
| Faridpur | 2,232,772 | 2,162,879 | 2048.7 | 2052.86 |
| Gopalganj | 1,336,907 | 1,295,057 | 1479.4 | 1468.74 |
| Rajbari | 1,228,267 | 1,189,818 | 1141.7 | 1118.80 |
| Shariatpur | 1,336,396 | 1,294,562 | 1187.9 | 1174.05 |
| Kishoreganj | 3,373,219 | 3,267,626 | 2570.7 | 2688.53 |
| Munshiganj | 1,677,941 | 1,625,416 | 935.0 | 954.96 |
| Madaripur | 1,334,811 | 1,293,027 | 1138.2 | 1125.69 |
| Tangail | 4,168,083 | 4,037,608 | 3373.7 | 3414.28 |

The seed has no Dhaka Division pourashavas (BBS 63).

## Unions vs the seed (BBS 887 vs seed 876), per upazila where the count differs

Name-matched with the HDX matcher; spelling-only differences are not listed.

| Upazila | BBS | Seed | Difference |
|---|---:|---:|---|
| Gazipur Sadar | 4 | 8 | Basan, Gachha, Kashimpur, Kayaltia, Konabari and Pubail are city-corporation thanas/areas in BBS 2022, not unions; BBS Bhawalgar and Pirujali not paired with a seed union |
| Narayanganj Sadar | 7 | 6 | Fatullah only in BBS |
| Raipura | 24 | 22 | Mirzapur, Radhanagar only in BBS |
| Belabo | 8 | 9 | Diara only in seed |
| Boalmari / Faridpur Sadar | 10 / 12 | 11 / 11 | BBS puts Chandpur under Faridpur Sadar (seed: Boalmari); North Channel (BBS) vs Uttarchannel (seed) |
| Madhukhali | 11 | 9 | Arpara, Korakdi, Kamaldia only in BBS; seed "Madhukhali" union not in BBS |
| Kalukhali | 7 | 8 | seed "Kalukhali" union not in BBS |
| Naria | 14 | 13 | Chamta, Fatejangapur (BBS) vs Fategongpur (seed) |
| Pakundia | 9 | 10 | seed "Pakundia" union not in BBS |
| Tongibari | 13 | 12 | BBS Arial and Baligaon vs seed "Arial Baligaon" |
| Kalkini / Dasar | 10 / 5 | 14 / 0 | BBS puts Baligram, Dasar, Gopalpur, Kazibakai and Nabagram under the new Dasar upazila; the seed keeps them under Kalkini. Purbaenayetnagar only in BBS |
| Ghatail | 14 | 11 | Lakkhindar, Sagardighi, Sangrampur only in BBS |
| Madhupur | 11 | 6 | Beribaid, Fulbagchala, Kuragachha, Kuralia, Mahishmara only in BBS |
| Sakhipur | 10 | 8 | Bahuria, Barachaona, Hateya Rajabari only in BBS; Kalmegha only in seed |

These are census-frame counts as of mid-2022; later gazette changes are not reflected.

## Licence
No licence is stated on bbs.gov.bd. Facts only (names, codes, counts) are copied; attribution "Bangladesh Bureau of
Statistics, Population and Housing Census 2022".
