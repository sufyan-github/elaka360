# BBS Population and Housing Census 2022 — Rajshahi Division

Source key `BBS_CENSUS_2022` · census · trust level 4 · accessed 2026-11-12 · collected by `fetch.py`.

## What was obtained

All files come from the Bangladesh Bureau of Statistics Census 2022 page
<https://bbs.gov.bd/pages/static-pages/6922e073933eb65569e27220> ("Population & Housing Census 2022 — District Report &
Community Series"). The PDFs and Excel files are hosted on the national portal's object storage
(`objectstorage.ap-dcc-gazipur-1.oraclecloud15.com/…/office-bbs/…`). Exact URLs per file: `raw/resolved_urls.json`.

| Document | Used for | Date |
|---|---|---|
| **Community Report** (Community Series), Excel, one per district — sheet **C-01** "Household, Population and Sex Ratio by Location and Community, 2022" | Every geocoded unit (district → city corporation / upazila / thana → paurashava → union / ward → mauza → village/mahalla) with households, population by sex, rural/urban split | Community PDFs dated 2025 (Rajshahi PDF created 2 Jun 2025); Excel files on storage since 2024-12 path |
| **District Report: \<district\>** (District Series), PDF, 324–536 pages each | "Key Findings" table: administrative-unit counts, area (km²), density, enumerated population | Created May–June 2024 (PDF metadata; library catalogue: June 2024); re-uploaded to bbs.gov.bd May 2026 (Naogaon Aug 2026) |
| **Population and Housing Census 2022: Union Statistics**, PDF, 499 pp. | Table D01 (administrative units, households, population by district) | Uploaded 30-06-2025 |
| National Report Vol. 1 (Nov 2023), Post Enumeration Check report, Administrative Report (2025) | Consulted only (see "Adjusted vs enumerated") | — |

The big files (≈ 300 MB) are not committed. `fetch.py --cache DIR` re-downloads and re-parses them; `fetch.py --offline`
rebuilds `areas.csv`/`facts.csv` from the committed excerpts in `raw/`:

- `raw/c01_rajshahi_division.csv` (2.2 MB) — all C-01 rows of the 8 district Excel files (codes, printed names,
  households, population). It holds the 2022 village/mahalla list too (not copied into `areas.csv`).
- `raw/district_report_key_findings.txt` — text of the Key Findings table of each District Report, with PDF page numbers.
- `raw/union_statistics_D01.txt` — Table D01 rows for Rajshahi Division (PDF page 66).

## Coverage

| Level | Units with population + households |
|---|---|
| District | 8 / 8 |
| Upazila | 67 (all) |
| City corporation / metro thana | Rajshahi City Corporation + 6 thanas (Boalia, Chandrima, Kashiadanga, Matihar, Rajpara, Shah Makhdum) |
| Paurashava | 62 rows = 61 paurashavas (Bogura Paurashava is printed in two parts: Bogura Sadar 422,969 + Shajahanpur 63,047) |
| Union | 566 (Bogura 109, Naogaon 99, Sirajganj 83, Pabna 74, Rajshahi 72, Natore 52, Chapainawabganj 45, Joypurhat 32) |
| Ward | 622 rows (city-corporation and paurashava wards; wards split between thanas appear once per part) |
| Cantonment | Bogura Cantonment (Shajahanpur; 11,504 persons) — level `cantonment`, see below |
| Mauza | 11,339 rows in `areas.csv` (names + geocodes; no facts) |

`facts.csv`: 6,691 rows — population, households, male/female/hijra, rural/urban population (district, upazila, union),
derived unit counts (upazila, city corporation, thana, paurashava, district), and the printed district totals from the
District Reports and Union Statistics.

## Basis and definitions

- **Population = final enumerated count**, census moment 15 June 2022 (00:00), *including floating population*.
  It is **not** PEC-adjusted. `basis = enumerated`.
- **Households** in C-01 exclude floating households; Union Statistics D01 counts all households (incl. floating),
  so D01 is a few hundred higher (e.g. Rajshahi 775,245 vs 774,886).
- Urban (2022) = city corporation, cantonment, paurashava, growth centre and upazila headquarters (C-01 "Urban" rows).
- `basis = as stated` — a number printed in a BBS table (counts, area, density).
- `basis = derived` — counted by us from the geocoded rows of C-01 (unions, paurashavas, wards, mauzas, villages,
  mahallas per upazila). Check against the printed district totals:
  - unions, paurashava wards, villages and mahallas: derived = printed in every district
    (only Natore villages 1,363 derived/D01 vs 1,365 in the District Report table);
  - mauzas: derived counts are lower (e.g. Rajshahi 1,630 vs 1,678) because the printed totals also count
    depopulated mauzas, which have no C-01 row. Use the printed district totals for mauzas.
- Geocodes (`code_scheme = BBS_GEOCODE_2022`) are the C-01 columns joined with `-`, starting with division 50:
  `50-81` district · `50-81-10` upazila · `50-81-10-08` paurashava (2 digits) · `50-81-10-08-001` paurashava ward ·
  `50-81-10-109` union (3 digits) · `50-81-10-109-077` mauza · `50-81-66` city corporation · `50-81-66-22` thana ·
  `50-81-66-22-009` city ward. 2022 union codes are 3-digit and differ from the 2011 2-digit union codes.
- Names are the BBS English spellings; the generic words "Union", "Upazila", "Paurashava" are dropped from `name_en`
  (the printed name is in `notes` when different). The trailing `*` on mauza names is the C-01 marker "Asterisk (*)
  denotes Mauza" and is dropped. No Bangla names in these tables (`name_bn` empty).

## Adjusted vs enumerated (important for the seed)

BBS publishes PEC-adjusted population **only down to division level** (District Report preface; National Report Vol. 1
Table 3.1.4): Rajshahi Division enumerated 20,353,116 → adjusted 20,794,019 (net coverage error 2.75 % nationally).
No BBS document gives adjusted district or upazila figures.

The seed's district `population_2022` (`CITYPOP_ADJ`, basis "adjusted") is exactly BBS enumerated × 1.02166
(= 20,794,019 / 20,353,116) for every district, i.e. a proportional share of the division adjustment computed by the
aggregator, not a BBS figure:

| District | Seed (CITYPOP_ADJ) | BBS enumerated (C-01 / D01) | Seed − BBS | Seed area km² | BBS area km² |
|---|---:|---:|---:|---:|---:|
| Rajshahi | 2,978,156 | 2,915,009 | +63,147 (+2.17 %) | 2425.37 | 2425.37 |
| Natore | 1,900,213 | 1,859,922 | +40,291 | 1908.8 | 1900.19 |
| Naogaon | 2,844,921 | 2,784,599 | +60,322 | 3450.8 | 3435.65 (narrative) |
| Pabna | 2,972,654 | 2,909,624 | +63,030 | 2395.0 | 2376.13 |
| Sirajganj | 3,430,443 | 3,357,706 | +72,737 | 2499.9 | 2402.02 |
| Bogura | 3,815,192 | 3,734,297 | +80,895 | 2918.7 | 2898.68 |
| Chapainawabganj | 1,875,290 | 1,835,528 | +39,762 | 1689.3 | 1702.55 |
| Joypurhat | 977,150 | 956,431 | +20,719 | 962.2 | 1012.41 (table) / 965.44 (narrative) |

Seed upazila populations for Rajshahi District (`CITYPOP_RAJ`, enumerated) equal BBS C-01 exactly. Seed Rajshahi City
Corporation 552,791 (`WIKI_CC`) vs BBS 553,288 (C-01, incl. floating; male+female = 553,241). Seed "Bogura City
Corporation" 540,000 (`FE_BOGURA`, estimate, 69.9 km²) has no census counterpart: the 2022 census has **Bogura
Paurashava** = 486,016 (two parts above).

## Union counts — conflicts resolved by BBS 2022

The 2022 C-01 geocode list (also printed as "List of Geo-code of \<district\>" in each District Report) gives the union
list per upazila. Against the seed (`data/seed/geo/admin_areas.csv`):

| Conflict | BBS 2022 | Seed | Union only in BBS |
|---|---|---|---|
| RAJ-001/002 Rajshahi district 71 vs 72, Bagha 6 vs 7 | **72**; Bagha **7** | 71; Bagha 6 | **Chak Rajapur** (50-81-10-182; 10,798 persons) |
| PAB-001/002 Pabna 73 vs 74 | **74**; Bhangura **6** | 73; Bhangura 5 | **Mandatosh** (50-76-19-509; 9,154) |
| SIR-001/002 Sirajganj 82 vs 83, Ullapara 13 vs 14 | **83**; Ullapara **14** | 82; Ullapara 13 | **Kayra** (50-88-94-444; 21,139) |
| BOG-001/005 Bogura 108/109/110; Gabtali 11 vs 12, Sonatala 7 vs 6 | **109 unions** + Bogura Cantonment; Gabtali **12**, Sonatala **7** | 108; Gabtali 11, Sonatala 7 | **Sukhanpukur** (Gabtali, 50-10-40-732; 26,201) |

- Bogura "110" in the District Report Key Findings counts Bogura Cantonment (printed in the Union/Ward column,
  code 998, under Shajahanpur); Union Statistics D01 prints 109. Likewise its "13 paurashavas" counts Bogura Paurashava
  twice (it straddles Bogura Sadar and Shajahanpur); there are 12 distinct paurashavas. Master v3's "Gabtali 12 /
  Sonatala 6" is right about Gabtali, wrong about Sonatala (7 in BBS: Balua, Digdair, Jorgachha, Madhupur, Pakulla,
  Sonatala, Tekani Chukainagar).
- CNB-003 (Chapainawabganj): BBS lists Jhilim, Narayanpur, Shahjahanpur under **Sadar** (14); Parbatipur, Radhanagar,
  Rahanpur under **Gomastapur** (8); Ghorapakhia, Panka, Ujirpur under **Shibganj** (15); there is no "Trimohoni".
  The seed rows match BBS; the master register entries are the outliers. Gomastapur is 8, not 9 (CNB-002).
- Naogaon Raninagar: BBS "Raninagar Union" (50-64-85-677) is the seed's "Khatteshawr" (খট্টেশ্বর রাণীনগর).
- Pabna Atgharia: BBS "Lakkhipur" = seed "Laxshmipur" (spelling only).
- Natore (52; Singra 12, Lalpur 10, Gurudaspur 6, Bagatipara 5, Naldanga 5), Naogaon (99; Sadar 12, Badalgachhi 8),
  Joypurhat (32; Kalai 5, Khetlal 5) and Rajshahi Bagmara (16) agree with the seed; the "secondary atlas" counts in
  the master conflict register are not supported by BBS 2022.
- Paurashava counts: Naogaon has only **3** paurashavas in the census (Naogaon, Dhamoirhat, Nazipur).

These are census-frame counts as of mid-2022. Later gazette changes (e.g. Bogura's Mokamtala upazila / new unions
reported in 2026, BOG-002…004) are not reflected.

## Per-upazila summary (from C-01)

Mauzas listed = populated mauzas with a C-01 row (printed district totals also count depopulated mauzas).

| District | Upazila (BBS spelling) | Geocode | Population (enum.) | Households | Unions | Paurashavas | Mauzas listed | Villages | Mahallas | Seed unions |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Rajshahi | Rajshahi City Corporation | 50-81-66 | 553,288 | 133,650 | – | – | 55 | 0 | 203 |  |
| Rajshahi | Bagha | 50-81-10 | 195,888 | 53,727 | 7 | 2 | 85 | 75 | 47 | 6 **≠** |
| Rajshahi | Bagmara | 50-81-12 | 373,970 | 106,313 | 16 | 2 | 291 | 319 | 45 | 16 |
| Rajshahi | Charghat | 50-81-25 | 224,845 | 61,107 | 6 | 1 | 93 | 121 | 36 | 6 |
| Rajshahi | Durgapur | 50-81-31 | 197,713 | 56,331 | 7 | 1 | 111 | 108 | 20 | 7 |
| Rajshahi | Godagari | 50-81-34 | 376,386 | 92,719 | 9 | 2 | 353 | 400 | 50 | 9 |
| Rajshahi | Mohanpur | 50-81-53 | 186,904 | 52,681 | 6 | 1 | 155 | 139 | 17 | 6 |
| Rajshahi | Paba | 50-81-72 | 368,889 | 97,204 | 8 | 2 | 166 | 211 | 56 | 8 |
| Rajshahi | Puthia | 50-81-82 | 224,143 | 62,484 | 6 | 1 | 127 | 183 | 16 | 6 |
| Rajshahi | Tanore | 50-81-94 | 212,983 | 58,670 | 7 | 2 | 194 | 169 | 40 | 7 |
| Natore | Bagatipara | 50-69-09 | 140,699 | 38,450 | 5 | 1 | 93 | 138 | 17 | 5 |
| Natore | Baraigram | 50-69-15 | 308,923 | 84,374 | 7 | 2 | 154 | 190 | 35 | 7 |
| Natore | Gurudaspur | 50-69-41 | 234,342 | 63,952 | 6 | 1 | 99 | 109 | 18 | 6 |
| Natore | Lalpur | 50-69-44 | 306,357 | 82,039 | 10 | 1 | 201 | 219 | 16 | 10 |
| Natore | Naldanga | 50-69-55 | 135,318 | 37,504 | 5 | 1 | 83 | 97 | 16 | 5 |
| Natore | Natore Sadar | 50-69-63 | 352,967 | 94,585 | 7 | 1 | 162 | 199 | 33 | 7 |
| Natore | Singra | 50-69-91 | 381,316 | 100,939 | 12 | 1 | 340 | 411 | 40 | 12 |
| Naogaon | Atrai | 50-64-03 | 201,459 | 55,930 | 8 | 0 | 146 | 204 | 0 | 8 |
| Naogaon | Badalgachhi | 50-64-06 | 206,557 | 59,358 | 8 | 0 | 238 | 239 | 0 | 8 |
| Naogaon | Dhamoirhat | 50-64-28 | 194,181 | 54,689 | 8 | 1 | 208 | 242 | 29 | 8 |
| Naogaon | Manda | 50-64-47 | 380,588 | 110,075 | 14 | 0 | 290 | 299 | 0 | 14 |
| Naogaon | Mahadebpur | 50-64-50 | 308,666 | 86,611 | 10 | 0 | 295 | 301 | 0 | 10 |
| Naogaon | Naogaon Sadar | 50-64-60 | 447,903 | 119,013 | 12 | 1 | 230 | 211 | 62 | 12 |
| Naogaon | Niamatpur | 50-64-69 | 270,452 | 73,523 | 8 | 0 | 308 | 344 | 0 | 8 |
| Naogaon | Patnitala | 50-64-75 | 250,729 | 69,221 | 11 | 1 | 288 | 298 | 14 | 11 |
| Naogaon | Porsha | 50-64-79 | 147,021 | 37,047 | 6 | 0 | 146 | 246 | 0 | 6 |
| Naogaon | Raninagar | 50-64-85 | 192,226 | 52,205 | 8 | 0 | 167 | 176 | 0 | 8 |
| Naogaon | Sapahar | 50-64-86 | 184,817 | 47,718 | 6 | 0 | 139 | 233 | 0 | 6 |
| Pabna | Atgharia | 50-76-05 | 178,582 | 46,328 | 5 | 1 | 108 | 123 | 19 | 5 |
| Pabna | Bera | 50-76-16 | 301,494 | 73,059 | 9 | 1 | 118 | 158 | 30 | 9 |
| Pabna | Bhangura | 50-76-19 | 136,576 | 33,923 | 6 | 1 | 69 | 125 | 37 | 5 **≠** |
| Pabna | Chatmohar | 50-76-22 | 334,240 | 90,904 | 11 | 1 | 158 | 239 | 13 | 11 |
| Pabna | Faridpur | 50-76-33 | 140,399 | 35,419 | 6 | 1 | 44 | 89 | 16 | 6 |
| Pabna | Ishwardi | 50-76-39 | 390,402 | 99,220 | 7 | 1 | 100 | 124 | 40 | 7 |
| Pabna | Pabna Sadar | 50-76-55 | 711,588 | 180,910 | 10 | 1 | 240 | 289 | 51 | 10 |
| Pabna | Santhia | 50-76-72 | 410,767 | 105,951 | 10 | 1 | 170 | 231 | 27 | 10 |
| Pabna | Sujanagar | 50-76-83 | 305,576 | 77,651 | 10 | 1 | 152 | 183 | 24 | 10 |
| Sirajganj | Belkuchi | 50-88-11 | 401,172 | 96,110 | 6 | 1 | 105 | 136 | 19 | 6 |
| Sirajganj | Chouhali | 50-88-27 | 138,061 | 34,449 | 7 | 0 | 76 | 86 | 0 | 7 |
| Sirajganj | Kamarkhanda | 50-88-44 | 154,386 | 38,655 | 4 | 0 | 55 | 95 | 0 | 4 |
| Sirajganj | Kazipur | 50-88-50 | 281,442 | 74,843 | 12 | 1 | 101 | 161 | 12 | 12 |
| Sirajganj | Rayganj | 50-88-61 | 348,190 | 90,253 | 9 | 1 | 193 | 343 | 29 | 9 |
| Sirajganj | Shahjadpur | 50-88-67 | 601,633 | 147,529 | 13 | 1 | 158 | 286 | 31 | 13 |
| Sirajganj | Sirajganj Sadar | 50-88-78 | 631,928 | 155,401 | 10 | 1 | 191 | 305 | 69 | 10 |
| Sirajganj | Tarash | 50-88-89 | 211,853 | 56,576 | 8 | 0 | 171 | 206 | 0 | 8 |
| Sirajganj | Ullapara | 50-88-94 | 589,041 | 148,432 | 14 | 1 | 262 | 416 | 26 | 13 **≠** |
| Bogura | Adamdighi | 50-10-06 | 206,797 | 57,199 | 6 | 1 | 110 | 179 | 35 | 6 |
| Bogura | Bogura Sadar | 50-10-20 | 657,790 | 172,009 | 11 | 1 | 137 | 127 | 193 | 11 |
| Bogura | Dhunat | 50-10-27 | 307,521 | 84,503 | 10 | 1 | 90 | 209 | 17 | 10 |
| Bogura | Dupchachia | 50-10-33 | 195,075 | 54,921 | 6 | 2 | 116 | 198 | 70 | 6 |
| Bogura | Gabtali | 50-10-40 | 344,902 | 93,282 | 12 | 1 | 108 | 215 | 22 | 11 **≠** |
| Bogura | Kahaloo | 50-10-54 | 234,585 | 65,285 | 9 | 1 | 162 | 260 | 19 | 9 |
| Bogura | Nandigram | 50-10-67 | 200,294 | 53,818 | 5 | 1 | 206 | 228 | 22 | 5 |
| Bogura | Sariakandi | 50-10-81 | 276,199 | 82,835 | 12 | 1 | 109 | 178 | 17 | 12 |
| Bogura | Shajahanpur | 50-10-85 | 333,676 | 88,736 | 9 | 1 | 132 | 168 | 17 | 9 |
| Bogura | Sherpur | 50-10-88 | 383,539 | 103,924 | 10 | 1 | 222 | 326 | 20 | 10 |
| Bogura | Shibganj | 50-10-94 | 400,456 | 115,003 | 12 | 1 | 241 | 444 | 31 | 12 |
| Bogura | Sonatala | 50-10-95 | 193,463 | 53,410 | 7 | 1 | 101 | 126 | 21 | 7 |
| Chapainawabganj | Bholahat | 50-70-18 | 113,314 | 28,969 | 4 | 0 | 38 | 113 | 0 | 4 |
| Chapainawabganj | Gomastapur | 50-70-37 | 304,184 | 76,403 | 8 | 1 | 137 | 277 | 36 | 8 |
| Chapainawabganj | Nachole | 50-70-56 | 167,678 | 42,679 | 4 | 1 | 176 | 214 | 36 | 4 |
| Chapainawabganj | Chapainawabganj Sadar | 50-70-66 | 583,475 | 141,030 | 14 | 1 | 145 | 247 | 128 | 14 |
| Chapainawabganj | Shibganj | 50-70-88 | 666,877 | 158,899 | 15 | 1 | 177 | 425 | 32 | 15 |
| Joypurhat | Akkelpur | 50-38-13 | 144,693 | 41,188 | 5 | 1 | 116 | 147 | 16 | 5 |
| Joypurhat | Joypurhat Sadar | 50-38-47 | 315,205 | 86,499 | 9 | 1 | 179 | 192 | 87 | 9 |
| Joypurhat | Kalai | 50-38-58 | 146,055 | 42,695 | 5 | 1 | 106 | 150 | 40 | 5 |
| Joypurhat | Khetlal | 50-38-61 | 110,866 | 32,858 | 5 | 1 | 86 | 131 | 40 | 5 |
| Joypurhat | Panchbibi | 50-38-74 | 239,612 | 66,628 | 8 | 1 | 216 | 245 | 46 | 8 |

## Problems found in the BBS documents

- **Naogaon District Report**: its Key Findings table (PDF p. 25–26) contains **Jamalpur's** figures (7 upazilas,
  2,115.16 km², population 2,499,738, Jamalpur upazila list). `fetch.py` detects this and skips it. Naogaon district
  totals come from C-01 and Union Statistics D01 (99 unions, 3 paurashavas, 2,532 mauzas, 2,793 villages); the area
  3,435.65 km² comes from the report's English district profile (PDF p. 39) — no density printed for Naogaon.
- **Joypurhat** area: Key Findings 1,012.41 km² (2022 and 2011 columns; density 945 is computed from it) vs district
  profile narrative 965.44 km² (the 2001 figure). Both rows are in `facts.csv`.
- Natore and Pabna District Reports' "Population by Upazila" lines are a few persons lower than C-01 (they exclude the
  floating population); district totals match. Not used.
- No upazila- or union-level area (km²) is printed in any of these 2022 reports; upazila area/density stay empty.
- BBS spells some upazilas differently from the seed (Mahadebpur/Mohadevpur, Chouhali/Chauhali, Rayganj/Raigonj,
  Dupchachia/Dupchanchia, Nandigram/Nondigram, Sariakandi/Shariakandi, Dhunat/Dhunot, Ishwardi/Ishurdi,
  Atgharia/Atghoria, Nachole/Nachol, Gomastapur/Gomostapur, Badalgachhi/Badalgachi, Kamarkhanda/Kamarkhand).

## Licence

No licence is stated on the BBS pages or in the reports (`license: null`). The figures are official statistics
published for public use; only facts (names, codes, counts) are extracted, no report text.

## Not done / blocked

- Nothing blocked: bbs.gov.bd needs the Sectigo DV R36 intermediate (added at runtime from its AIA URL; TLS
  verification stays on). `pcs.icms.gov.bd` (cited elsewhere for district reports) does not resolve; the old
  `203.112.218.101` BBS server is unreachable — neither is needed.
- citypopulation.de was not needed (no `CITYPOP_RAJDIV_2026` folder).
- Village/mahalla names (≈ 17,000) are in `raw/c01_rajshahi_division.csv` but not in `areas.csv`.
- Preliminary Report (July 2022) figures were not collected; the final enumerated counts supersede them.
