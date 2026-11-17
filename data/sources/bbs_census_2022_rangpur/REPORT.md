# BBS Population and Housing Census 2022 — Rangpur Division

Source key `BBS_CENSUS_2022_RANGPUR` · census · trust level 4 · accessed 2026-11-17 · collected by
`python3 -I data/sources/bbs_census_2022/fetch.py --division rangpur` · division `rangpur` · kind `bbs_census`.

## What was obtained

Same documents and page as the Rajshahi run (<https://bbs.gov.bd/pages/static-pages/6922e073933eb65569e27220>), resolved
from the listing page on 2026-11-17 (exact URLs: `raw/resolved_urls.json`):

| Document | Used for |
|---|---|
| Community Report Excel per district (8), sheet **C-01** | every geocoded unit down to village/mahalla, households, population by sex, rural/urban |
| District Report PDFs (8; PDF creation dates 26 May – 11 Jun 2024, 302–512 pages) | Key Findings: unit counts, area, density |
| Union Statistics PDF (national, June 2025), Table D01, PDF page 66 | district unit counts, households, population |

Downloads ≈ 260 MB (not committed; `fetch.py --division rangpur` rebuilds; `--offline` rebuilds from `raw/`).
Committed excerpts:
- `raw/c01_rangpur_division.csv` (1.6 MB, 21,006 C-01 rows incl. 11,753 village/mahalla rows)
- `raw/district_report_key_findings.txt`
- `raw/union_statistics_D01.txt`
- `raw/resolved_urls.json`

## Coverage

| Level | Rows in areas.csv |
|---|---|
| District | 8 |
| Upazila | 58 |
| City corporation / metro thana | Rangpur City Corporation (55-85-75; 708,570 persons) + 6 thanas (Hajirhat, Haragachh, Kotwali, Mahiganj, Parshuram, Tajhat) |
| Paurashava | 31 (Dinajpur 9, Gaibandha 4, Nilphamari 4, Kurigram 3, Thakurgaon 3, Rangpur 3, Panchagarh 3, Lalmonirhat 2) |
| Union | 535 (Dinajpur 103, Gaibandha 81, Rangpur 76, Kurigram 73, Nilphamari 60, Thakurgaon 54, Lalmonirhat 45, Panchagarh 43) |
| Ward | 327 rows: 279 paurashava wards (Saidpur 15, Dinajpur and Thakurgaon 12, the others 9) + 48 City Corporation ward rows (33 numbered wards; 15, 28 and 29 are split between thanas, so they appear once per part) |
| Cantonment | 2: Saidpur Cantonment (55-73-85-998, Union/Ward column under Saidpur; 2,826 persons) and "Cantonment" (55-85-75-44-998, a ward-coded row in Kotwali Thana; 5,243 persons) |
| Mauza | 7,083 rows (names + geocodes; no facts) |

`facts.csv`: 5,602 rows, with the same fact set, `basis` values and code scheme (`BBS_GEOCODE_2022`, division prefix 55) as the Rajshahi run.
No Bangla names in the source.

## Basis

- **Population** is the final enumerated count incl. floating population, not PEC-adjusted.
- **Households** in D01 include floating households, so they are slightly higher than C-01.
- **Division enumerated total** (D01): 17,610,955.

The seed's district `population_2022` (`CITYPOP_ADJ`, "adjusted") equals the BBS enumerated count × 1.02323 for every district (seed division 18,020,071 / 17,610,955). It is a proportional share computed by the aggregator, not a BBS figure.
I did not check the 18,020,071 total against a BBS adjusted figure, because the National Report was not downloaded.

| District | Seed (CITYPOP_ADJ) | BBS enumerated | Seed area km² | BBS area km² (Key Findings) |
|---|---:|---:|---:|---:|
| Rangpur | 3,243,247 | 3,169,614 | 2348.5 | 2400.56 |
| Dinajpur | 3,392,251 | 3,315,236 | 3466.7 | 3444.30 |
| Gaibandha | 2,621,756 | 2,562,233 | 2171.3 | 2114.77 |
| Kurigram | 2,383,268 | 2,329,160 | 2279.0 | 2245.04 |
| Nilphamari | 2,141,180 | 2,092,568 | 1591.2 | 1546.59 |
| Thakurgaon | 1,569,529 | 1,533,895 | 1818.5 | 1781.74 |
| Lalmonirhat | 1,461,589 | 1,428,406 | 1277.1 | 1247.37 |
| Panchagarh | 1,207,252 | 1,179,843 | 1364.8 | 1495.70 |

Rangpur City Corporation: BBS 708,570 (C-01, incl. floating) vs seed 708,384 (`WIKI_CC`).

## Printed vs derived counts (conflicts inside BBS)

- **Unions.** Key Findings, D01 and the count derived from C-01 agree for every district except Nilphamari: Key Findings 61, D01 60. The derived count is 60 plus Saidpur Cantonment, so the Key Findings figure counts the cantonment (as Bogura's did in Rajshahi).
- **Rangpur villages.** Key Findings 2,959 vs D01 1,301 (derived from C-01 = 1,301). The other districts agree.
- **Rangpur city wards.** Key Findings 33, D01 37. C-01 has 33 numbered wards (3 split between thanas) plus the Cantonment row.
- **Mauzas.** Key Findings and D01 agree in all districts. The derived counts differ both ways, because mauzas split across upazilas are counted once per upazila and depopulated mauzas have no row. Use the printed totals.

  | District | Key Findings / D01 | Derived from C-01 |
  |---|---:|---:|
  | Rangpur | 1,226 | 1,228 |
  | Gaibandha | 1,082 | 1,105 |
  | Nilphamari | 387 | 372 |
  | Kurigram | 616 | 631 |
  | Dinajpur | 2,017 | 2,033 |
  | Thakurgaon | 651 | 649 |
  | Lalmonirhat | 352 | 353 |
  | Panchagarh | 425 | 401 |
- **Paurashavas.** BBS has 31; DGHS and the HDX 2020 points have 28 each. BBS adds Birol (Dinajpur), Debiganj (Panchagarh) and Pirganj (Rangpur). The seed has no Rangpur pourashavas.

## Unions vs the seed (data/seed/geo/admin_areas.csv), BBS 535 vs seed 540

| Upazila | BBS 2022 | Seed | Difference |
|---|---:|---:|---|
| Rangpur Sadar | 5 | 11 | Seed unions Uttam, Porshuram, Topodhan, Satgara, Rajendrapur, Dorshona and Tampat are not unions in 2022: their mauzas appear as "(Part)" mauzas inside City Corporation thanas. BBS puts Khaleya under Rangpur Sadar; the seed has Kholeya under Gangachara. |
| Gangachara | 9 | 10 | Kholeya (see above) |
| Palashbari (Gaibandha) | 8 | 9 | Seed "Palashbari" union not in BBS 2022 (it is in the HDX 2020 points) |
| Birol (Dinajpur) | 12 | 11 | "Palashbari" union only in BBS |
| Roumari | 6 | 5 | "Char Shoulmari" only in BBS |
| Thakurgaon Sadar | 22 | 21 | "Senua" only in BBS |

Spelling-only differences: these are the same union, but the matcher did not pair them.

| BBS 2022 | Seed |
|---|---|
| Kolkonda | Kolcondo |
| Kaunia Balapara | Balapara |
| Kursha (Kaunia) | Kurshaupk |
| Kursha (Taraganj) | Kurshatara |
| Bara Darga | Borodargah |
| Khorda Komarpur | Khodkomor |
| Dahabanda | Dohbond |
| Dantbhanga | Dadevanga |
| Akcha | Ahcha |
| Benghari Banagram | Banghari |
| Chhaola | Saula (probable) |

These are census-frame counts as of mid-2022; later gazette changes are not reflected.

## Per-upazila summary (from C-01; Mauzas listed = distinct populated mauza codes)

| District | Upazila (BBS) | Geocode | Population (enum.) | Households | Unions | Paurashavas | Mauzas listed | Seed unions |
|---|---|---|---:|---:|---:|---:|---:|---:|
| Rangpur | Rangpur City Corporation | 55-85-75 | 708,570 | 170,641 | – | – | 124 | |
| Rangpur | Badarganj | 55-85-03 | 314,865 | 82,135 | 10 | 1 | 66 | 10 |
| Rangpur | Gangachara | 55-85-27 | 286,730 | 73,969 | 9 | 0 | 85 | 10 ≠ |
| Rangpur | Kaunia | 55-85-42 | 239,689 | 63,121 | 6 | 1 | 78 | 6 |
| Rangpur | Rangpur Sadar | 55-85-49 | 178,675 | 46,047 | 5 | 0 | 49 | 11 ≠ |
| Rangpur | Mithapukur | 55-85-58 | 538,723 | 152,544 | 17 | 0 | 309 | 17 |
| Rangpur | Pirgachha | 55-85-73 | 326,622 | 91,311 | 9 | 0 | 168 | 9 |
| Rangpur | Pirganj | 55-85-76 | 414,845 | 114,097 | 15 | 1 | 307 | 15 |
| Rangpur | Taraganj | 55-85-92 | 160,895 | 40,274 | 5 | 0 | 40 | 5 |
| Gaibandha | Fulchhari | 55-32-21 | 166,662 | 44,910 | 7 | 0 | 65 | 7 |
| Gaibandha | Gaibandha Sadar | 55-32-24 | 499,196 | 131,599 | 13 | 1 | 137 | 13 |
| Gaibandha | Gobindaganj | 55-32-30 | 543,144 | 149,955 | 17 | 1 | 335 | 17 |
| Gaibandha | Palashbari | 55-32-67 | 267,438 | 73,267 | 8 | 1 | 160 | 9 ≠ |
| Gaibandha | Sadullapur | 55-32-82 | 313,628 | 88,018 | 11 | 0 | 158 | 11 |
| Gaibandha | Saghata | 55-32-88 | 289,628 | 79,700 | 10 | 0 | 116 | 10 |
| Gaibandha | Sundarganj | 55-32-91 | 482,537 | 132,780 | 15 | 1 | 111 | 15 |
| Nilphamari | Dimla | 55-73-12 | 316,846 | 76,170 | 10 | 0 | 53 | 10 |
| Nilphamari | Domar | 55-73-15 | 282,630 | 69,103 | 10 | 1 | 59 | 10 |
| Nilphamari | Jaldhaka | 55-73-36 | 386,801 | 93,754 | 11 | 1 | 70 | 11 |
| Nilphamari | Kishoreganj | 55-73-45 | 269,332 | 68,633 | 9 | 0 | 50 | 9 |
| Nilphamari | Nilphamari Sadar | 55-73-64 | 523,966 | 124,246 | 15 | 1 | 110 | 15 |
| Nilphamari | Saidpur | 55-73-85 | 312,993 | 73,574 | 5 | 1 | 45 | 5 |
| Kurigram | Bhurungamari | 55-49-06 | 255,548 | 69,120 | 10 | 0 | 56 | 10 |
| Kurigram | Rajibpur | 55-49-08 | 78,383 | 19,398 | 3 | 0 | 21 | 3 |
| Kurigram | Chilmari | 55-49-09 | 131,715 | 34,576 | 6 | 0 | 45 | 6 |
| Kurigram | Phulbari | 55-49-18 | 186,682 | 48,154 | 6 | 0 | 49 | 6 |
| Kurigram | Kurigram Sadar | 55-49-52 | 361,408 | 90,115 | 8 | 1 | 80 | 8 |
| Kurigram | Nageshwari | 55-49-61 | 444,699 | 112,330 | 14 | 1 | 80 | 14 |
| Kurigram | Rajarhat | 55-49-77 | 203,060 | 53,625 | 7 | 0 | 109 | 7 |
| Kurigram | Roumari | 55-49-79 | 227,513 | 57,569 | 6 | 0 | 29 | 5 ≠ |
| Kurigram | Ulipur | 55-49-94 | 440,152 | 120,793 | 13 | 1 | 147 | 13 |
| Dinajpur | Birampur | 55-27-10 | 184,144 | 49,692 | 7 | 1 | 169 | 7 |
| Dinajpur | Birganj | 55-27-12 | 356,152 | 87,824 | 11 | 1 | 190 | 11 |
| Dinajpur | Birol | 55-27-17 | 281,554 | 69,194 | 12 | 1 | 240 | 11 ≠ |
| Dinajpur | Bochaganj | 55-27-21 | 171,718 | 43,405 | 6 | 1 | 144 | 6 |
| Dinajpur | Chirirbandar | 55-27-30 | 323,880 | 78,147 | 12 | 0 | 142 | 12 |
| Dinajpur | Fulbari | 55-27-38 | 194,569 | 50,295 | 7 | 1 | 162 | 7 |
| Dinajpur | Ghoraghat | 55-27-43 | 131,413 | 35,183 | 4 | 1 | 113 | 4 |
| Dinajpur | Hakimpur | 55-27-47 | 95,972 | 25,248 | 3 | 1 | 69 | 3 |
| Dinajpur | Kaharole | 55-27-56 | 174,564 | 42,806 | 6 | 0 | 153 | 6 |
| Dinajpur | Khansama | 55-27-60 | 197,402 | 47,537 | 6 | 0 | 57 | 6 |
| Dinajpur | Dinajpur Sadar | 55-27-64 | 549,184 | 135,479 | 10 | 1 | 221 | 10 |
| Dinajpur | Nababganj | 55-27-69 | 254,036 | 67,750 | 9 | 0 | 204 | 9 |
| Dinajpur | Parbatipur | 55-27-77 | 400,648 | 104,139 | 10 | 1 | 153 | 10 |
| Thakurgaon | Baliadangi | 55-94-08 | 208,350 | 52,437 | 8 | 0 | 78 | 8 |
| Thakurgaon | Haripur | 55-94-51 | 159,516 | 39,144 | 6 | 0 | 74 | 6 |
| Thakurgaon | Pirganj | 55-94-82 | 265,159 | 67,184 | 10 | 1 | 176 | 10 |
| Thakurgaon | Ranishankail | 55-94-86 | 244,078 | 61,279 | 8 | 1 | 128 | 8 |
| Thakurgaon | Thakurgaon Sadar | 55-94-94 | 656,792 | 162,239 | 22 | 1 | 195 | 21 ≠ |
| Lalmonirhat | Aditmari | 55-52-02 | 251,229 | 60,721 | 8 | 0 | 56 | 8 |
| Lalmonirhat | Hatibandha | 55-52-33 | 264,107 | 63,419 | 12 | 0 | 63 | 12 |
| Lalmonirhat | Kaliganj | 55-52-39 | 277,024 | 68,037 | 8 | 0 | 64 | 8 |
| Lalmonirhat | Lalmonirhat Sadar | 55-52-55 | 373,470 | 91,859 | 9 | 1 | 120 | 9 |
| Lalmonirhat | Patgram | 55-52-70 | 262,576 | 57,832 | 8 | 1 | 49 | 8 |
| Panchagarh | Atwari | 55-77-04 | 141,549 | 35,352 | 6 | 0 | 61 | 6 |
| Panchagarh | Boda | 55-77-25 | 275,282 | 67,429 | 10 | 1 | 158 | 10 |
| Panchagarh | Debiganj | 55-77-34 | 267,466 | 64,550 | 10 | 1 | 97 | 10 |
| Panchagarh | Panchagarh Sadar | 55-77-73 | 335,366 | 77,784 | 10 | 1 | 76 | 10 |
| Panchagarh | Tetulia | 55-77-90 | 160,180 | 36,471 | 7 | 0 | 33 | 7 |

## Licence
No licence is stated on bbs.gov.bd. Facts only (names, codes, counts) are copied; attribution "Bangladesh Bureau of
Statistics, Population and Housing Census 2022".
