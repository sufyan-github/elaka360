# BBS Population and Housing Census 2022 — Sylhet Division

Source key `BBS_CENSUS_2022_SYLHET` · census · trust level 4 · accessed 2026-11-18 · collected by
`python3 -I data/sources/bbs_census_2022/fetch.py --division sylhet` · division `sylhet` · kind `bbs_census`.

## What was obtained

Same page as the earlier runs (<https://bbs.gov.bd/pages/static-pages/6922e073933eb65569e27220>), resolved on
2026-11-18 (exact URLs: `raw/resolved_urls.json`):

| Document | Used for |
|---|---|
| Community Report Excel per district (4), sheet **C-01** | every geocoded unit down to village/mahalla, households, population by sex, rural/urban |
| District Report PDFs (4; PDF creation dates 2 May – 12 Jun 2024, 348–540 pages) | Key Findings (PDF pages 25–27): unit counts, area, density |
| Union Statistics PDF (national, June 2025), Table D01, PDF page 66 | district unit counts, households, population |

Downloads ≈ 160 MB (not committed; `fetch.py --division sylhet` rebuilds; `--offline` rebuilds from `raw/`).
Committed: `raw/c01_sylhet_division.csv` (1.3 MB, 18,420 C-01 rows incl. 11,534 village/mahalla rows, as printed),
`raw/district_report_key_findings.txt`, `raw/union_statistics_D01.txt`, `raw/resolved_urls.json`. areas.csv 1.9 MB
(6,114 rows), facts.csv 1.3 MB (3,608 rows); same fact set, `basis` values and code scheme (`BBS_GEOCODE_2022`,
division prefix 60) as the earlier runs. No Bangla names in the source.

fetch.py change for this run: Sylhet district table (order of the Community Report list on the BBS page; labels as
printed there; geocodes checked against the first C-01 row of each Excel): Sylhet 91, Habiganj 36, Moulvibazar 58
(page label MAULVIBAZAR), Sunamganj 90. No other change was needed: the C-01 headers, sheet names and labels matched
the existing rules.

Earlier divisions unchanged:
- Rajshahi, full run with no `--division` (live downloads) into a scratch `--out`: areas.csv, facts.csv and all four raw
  files byte-identical with the committed folder (including `raw/resolved_urls.json`).
- Rangpur/Dhaka/Chattogram/Khulna/Barishal: URL resolution on the current listing page identical to each committed
  `raw/resolved_urls.json`; `--offline` rebuilds from the committed raw/ byte-identical.
- No difference came from a live source or a seed change.

## Coverage

| District | Geocode | Population (enum.) | Households | Upazilas | City corp. / thanas | Paurashavas | Unions | Paura wards | City wards | Mauza rows |
|---|---|---:|---:|---:|---|---:|---:|---:|---:|---:|
| Sylhet | 60-91 | 3,857,123 | 746,406 | 13 | 1 / 6 | 5 | 108 | 45 | 27 | 1,700 |
| Habiganj | 60-36 | 2,358,886 | 491,756 | 9 | – | 6 | 78 | 54 | – | 1,227 |
| Moulvibazar | 60-58 | 2,123,447 | 446,229 | 7 | – | 5 | 67 | 45 | – | 980 |
| Sunamganj | 60-90 | 2,695,496 | 528,410 | 12 | – | 4 | 88 | 36 | – | 1,586 |
| **Division** | 60 | **11,034,952** | | **41** | **1 / 6** | **20** | **341** | **180** | **27** | **5,493** |

Division totals agree with the D01 division row: 1 city corporation, 6 metro thanas, 27 city wards, 41 upazilas,
20 paurashavas, 180 paura wards, 341 unions. D01 also prints 5,473 mauzas, 1,034 mahallas and 10,500 villages.
New upazilas present in the 2022 frame: Osmaninagar (60-91-60), Shayestaganj (60-36-87, with Shayestaganj Paurashava),
Madhyanagar (60-90-63, 4 unions) and Shantiganj (60-90-87, 8 unions).

**Non-union units in the Union/Ward column:**
- **Cantonment Union** (60-91-62-998, Sylhet Sadar upazila; population 9,447). It is kept at level `cantonment`,
  with a `cantonment_count` fact for Sylhet Sadar and Sylhet district. It is not counted as a union.
- No 997 (forest) row exists.
- No tea-estate, forest or haor unit is printed in the Union/Ward column. Tea estates ("… Te", "… Tea Garden",
  "… Tea Estate", e.g. Manipur Tea Estate, Rashidpur Te), reserve forests (Khadimnagar, Dinarpur, Taraf Hill,
  Raghunandan Hill, Lauraga Reserve Forest) and haors appear only as mauza rows inside unions (and one in the Cantonment).
  They stay at level `mouza`.
- Zakiganj Union has code 942. It is a union ("… Union", with Rural/Urban rows) and stays at level `union`.
- No unit above mauza level is marked "(Part)". 755 mauza rows are "(Part)": 472 under unions, 282 under wards and 1
  under the Cantonment.

## Sylhet City Corporation (geocode 60-91-50, seed 50006 in Sylhet district 20036)

- Population 532,839 (C-01). The seed has 532,426 (`WIKI_CC`, census).
- **6 metro thanas:**
  - Airport (60-91-50-05): 4 wards
  - Dakkhin Surma (60-91-50-31): 2 wards
  - Jalalabad (60-91-50-48): 1 ward
  - Kotwali (60-91-50-55): 15 wards
  - Moglabazar (60-91-50-57): 1 ward
  - Shahparan (60-91-50-68): 4 wards
- **27 wards (Ward No. 01–27)**, one row each, none split. `ward_count` = 27, the same as the Key Findings "City Ward" figure (27) and D01.
- 327 mahallas and 23 mauza codes; no unions inside the city corporation.
- Two thana codes repeat upazila codes outside the city:
  - Thana 31 Dakkhin Surma = Dakkhin Surma upazila 60-91-31 (10 unions).
  - The city wards sit under 2020 Sylhet Sadar in HDX, and Sylhet Sadar upazila is 60-91-62.
  - Always use the full geocode (60-91-50-…).

## Printed vs derived counts (conflicts inside BBS)

- **Upazilas, paurashavas, paura wards, villages, mahallas, population:** Key Findings, D01 and the derived counts agree in every district.
- **Unions:** they agree in Habiganj, Moulvibazar and Sunamganj. In Sylhet, the Key Findings print 109 while D01 and
  C-01 have 108. The difference equals the Cantonment row, which C-01 prints in the Union/Ward column (as in Rajshahi).
- **Mauzas:** Key Findings = D01 in every district: Sylhet 1,681, Habiganj 1,246, Moulvibazar 889, Sunamganj 1,657
  (incl. depopulated mauzas). The derived distinct counts are lower (1,592 / 1,113 / 866 / 1,521). Use the printed totals.
- **Households:** D01 includes floating households, so it is slightly higher than C-01.
- **Area:** the Key Findings figure equals the English profile narrative for Habiganj (2,636.58) and Sunamganj (3,747.18).
  The Sylhet (3,452.07) and Moulvibazar (2,799.38) reports have no narrative figure.

## Basis and seed comparison

Population is the final enumerated count incl. floating population, not PEC-adjusted. Division enumerated total (D01):
11,034,952. The seed district `population_2022` (`CITYPOP_ADJ`, "adjusted") equals BBS enumerated × 1.03445 for every
district (seed division 11,415,113). It is a proportional figure computed by the aggregator, not a BBS figure.

| District | Seed (CITYPOP_ADJ) | BBS enumerated | Seed area km² | BBS area km² (Key Findings) |
|---|---:|---:|---:|---:|
| Sylhet | 3,990,003 | 3,857,123 | 3425.1 | 3452.07 |
| Moulvibazar | 2,196,601 | 2,123,447 | 2684.5 | 2799.38 |
| Habiganj | 2,440,151 | 2,358,886 | 2588.3 | 2636.58 |
| Sunamganj | 2,788,358 | 2,695,496 | 3701.3 | 3747.18 |

The seed areas are computed from polygons. The seed has no Sylhet Division pourashavas (BBS 20).

## Upazilas and unions vs the seed (BBS 41 / 341 vs seed 41 / 336)

Name-matched with the HDX matcher (direction words read as North/South/East/West). Upazila pairs were checked against
the seed's Bangla names. Spelling-only differences are not listed.
- All upazilas pair by name except **Shantiganj** (60-90-87). Correct-but-medium pairs: Dakkhin Surma = Dakshinsurma
  (দক্ষিণ সুরমা), Jaintapur = Jaintiapur (জৈন্তাপুর), Baralekha = Barlekha (বড়লেখা), Kamalganj = Kamolganj (কমলগঞ্জ).
- Shantiganj is the seed's **South Sunamganj** (দক্ষিণ সুনামগঞ্জ, 30301), hand-checked on three counts:
  - the seed's Bangla name is the upazila's former name, Dakshin Sunamganj;
  - HDX's 2020 point for the same unions is named "Dakshin Sunamganj";
  - BBS Shantiganj's 8 unions are the seed South Sunamganj's 8 unions (Shimulbank = Shimulbak by fuzzy match; the others exact or skeleton).
- Madhyanagar (60-90-63) = seed Madhyanagar (মধ্যনগর, 30493). The seed has no unions under it.

| Upazila (BBS) | BBS | Seed | Difference |
|---|---:|---:|---|
| Golapganj | 11 | 10 | Bagha only in BBS |
| Gowainghat | 12 | 9 | Gowainghat Sadar, Maddho Jaflong, Pashchim Alirgaon, Purba Alirgaon only in BBS; Alirgaon (আলীরগাঁও) only in the seed |
| Dharmapasha | 6 | 10 | the seed also holds Madhyanagar's 4 unions (Chamordani, Madhyanagar, Bongshikunda North/South); BBS Rajapur and Sukhair vs seed Sukhair Rajapur North/South (সুখাইড় রাজাপুর উত্তর/দক্ষিণ) not paired |
| Madhyanagar | 4 | 0 | Chamardani, Dakkhin Bangshikunda, Madhyanagar, Uttar Bangshikunda (in the seed under Dharmapasha) |
| Jamalganj | 6 | 5 | Jamalganj Uttar only in BBS |

Pairs the matcher does not make, but which are the same union by the seed's Bangla name:
- Uttar Ranikhai ~ Uttor Ronikhai (উত্তর রনিখাই, Companiganj)
- Pashchim / Purba Lakkhiprasad ~ Lakshiprashad Pashim / Purbo (লক্ষীপ্রাসাদ পশ্চিম / পূর্ব, Kanaighat)
- Purba Dighirpar ~ Digirpar Purbo (দিঘিরপার পূর্ব, Kanaighat)
- Dhaka Dakkhin ~ Dhakadakshin (ঢাকাদক্ষিন, Golapganj)
- Uttarbhag ~ Uttorbhag (উত্তরভাগ, Rajnagar)
- Kakailchheo ~ Kakailsao (কাকাইলছেও, Ajmiriganj)
- Pail ~ Poil (পইল, Habiganj Sadar)
- Uttar Purba / Uttar Pashchim / Dakkhin Purba / Dakkhin Pashchim Baniachong ~ Baniachong North East / North West /
  South East / South West (বানিয়াচং উত্তর পূর্ব …)

Not the same name, left unpaired: Kurbannagar (BBS, Sunamganj Sadar) vs Aptabnagar (আপ্তাবনগর, seed).

Low-confidence matcher pairs to review: Ichhakalas~Isakalas, Kajalsar~Kajalshah, Bamai~Bamoi, Lakkhipur~Laxmipur,
Fenarbank~Fenerbak.

These are census-frame counts as of mid-2022; later gazette changes are not reflected.

## Licence
No licence is stated on bbs.gov.bd. Facts only (names, codes, counts) are copied; attribution "Bangladesh Bureau of
Statistics, Population and Housing Census 2022".
