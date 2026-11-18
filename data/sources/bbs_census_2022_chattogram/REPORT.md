# BBS Population and Housing Census 2022 — Chattogram Division

Source key `BBS_CENSUS_2022_CHATTOGRAM` · census · trust level 4 · accessed 2026-11-17 · collected by
`python3 -I data/sources/bbs_census_2022/fetch.py --division chattogram` · division `chattogram` · kind `bbs_census`.

## What was obtained

Same page as the Rajshahi/Rangpur/Dhaka runs (<https://bbs.gov.bd/pages/static-pages/6922e073933eb65569e27220>), resolved
on 2026-11-17 (exact URLs: `raw/resolved_urls.json`):

| Document | Used for |
|---|---|
| Community Report Excel per district (11), sheet **C-01** | every geocoded unit down to village/mahalla, households, population by sex, rural/urban |
| District Report PDFs (11; PDF creation dates 23 May – 12 Jun 2024, 334–644 pages) | Key Findings: unit counts, area, density |
| Union Statistics PDF (national, June 2025), Table D01, PDF page 65 | district unit counts, households, population |

Downloads ≈ 300 MB (not committed; `fetch.py --division chattogram` rebuilds; `--offline` rebuilds from `raw/`).
Committed: `raw/c01_chattogram_division.csv` (2.4 MB, 31,913 C-01 rows incl. 19,184 village/mahalla rows),
`raw/district_report_key_findings.txt`, `raw/union_statistics_D01.txt`, `raw/resolved_urls.json`.
areas.csv 3.2 MB (10,579 rows), facts.csv 3.7 MB (10,198 rows); same fact set, `basis` values and code scheme
(`BBS_GEOCODE_2022`, division prefix 20) as the earlier runs. No Bangla names in the source.

fetch.py changes for this run:
- Chattogram district table.
- Community-report links: Noakhali and Feni print their label as a link ("{NOAKHALI|…} : {PDF|…}, {Excel|…}"), now
  accepted.
- C-01 parsing:
  - Cox's Bazar's sheet has an extra, empty "Area (Acres)" column before the household columns (and a "Population
    Density" column after "Sex Ratio"); the household/population columns are read after it.
  - One unlabelled row with all zeros (Cumilla, under Comilla Cantonment, after its "Urban" row) is skipped.
- Key Findings parsing:
  - Labels may contain an apostrophe ("Cox’s Bazar").
  - Control characters left by pdftotext are removed (Chandpur printed "1273\x03" for villages).
  - Where "City Mahalla" and "Mahalla" are printed on separate lines (Chattogram), neither is kept as the district
    mahalla total.

Rajshahi/Rangpur/Dhaka outputs are unchanged:
- URL resolution, old vs new code on the current listing page: identical.
- C-01 re-extracted from freshly downloaded Excel files: byte-identical to the committed raw CSVs.
- `--offline` rebuilds of areas.csv/facts.csv: byte-identical.
- The district PDFs were not downloaded again; the PDF extraction code is unchanged.

## Coverage

| District | Geocode | Population (enum.) | Households | Upazilas | City corp. / thanas | Paurashavas | Unions | Paura wards | City ward rows | Mauza rows |
|---|---|---:|---:|---:|---|---:|---:|---:|---:|---:|
| Chattogram | 20-15 | 9,169,465 | 2,141,904 | 15 | 1 / 15 | 14 | 192 | 126 | 55 | 1,144 |
| Cox's Bazar | 20-22 | 2,823,268 | 586,852 | 9 | – | 4 | 71 | 39 | – | 233 |
| Bandarban | 20-03 | 481,106 | 106,065 | 7 | – | 2 | 34 | 18 | – | 119 |
| Rangamati | 20-84 | 647,586 | 153,430 | 10 | – | 2 | 50 | 18 | – | 183 |
| Noakhali | 20-75 | 3,625,442 | 775,704 | 9 | – | 8 | 91 | 72 | – | 1,024 |
| Feni | 20-30 | 1,648,896 | 376,773 | 6 | – | 5 | 43 | 54 | – | 593 |
| Cumilla | 20-19 | 6,212,216 | 1,406,975 | 17 | 1 / 2 | 8 | 193 | 72 | 27 | 2,721 |
| Chandpur | 20-13 | 2,635,748 | 635,290 | 8 | – | 7 | 89 | 75 | – | 1,075 |
| Brahmanbaria | 20-12 | 3,306,563 | 711,937 | 9 | – | 5 | 100 | 48 | – | 972 |
| Khagrachhari | 20-46 | 714,119 | 169,443 | 9 | – | 3 | 38 | 27 | – | 153 |
| Lakshmipur | 20-51 | 1,937,948 | 459,236 | 5 | – | 4 | 58 | 42 | – | 533 |
| **Division** | 20 | **33,202,357** | | **104** | **2 / 17** | **62** | **959** | **591** | **82** | **8,750** |

Division totals agree with the D01 division row (2 city corporations, 17 metro thanas, 82 city wards, 104 upazilas,
62 paurashavas, 591 paura wards, 959 unions; D01 also prints 8,207 mauzas, 2,367 mahallas, 16,817 villages).

**Cantonments:**
- Only one is printed in the Union/Ward column: Comilla Cantonment, as "Cantonment" (20-19-67-998, under Adarsha
  Sadar, enumerated population 13,467). It is level `cantonment`, not a union parishad.
- Three other rows named "Cantonment" are village/mahalla rows, not separate units, so they are not in areas.csv: a
  mahalla in Chattogram City Ward 01 (Bayejid Bostami), a village in Ramu (Cox's Bazar) and a village in Alikadam
  (Bandarban).

## City corporations (kept apart by the city-corporation code in the geocode)

| City corporation | Geocode | Seed id | Population (C-01) | Seed (WIKI_CC) | Thanas | Wards | Ward rows | Mahallas | Mauzas listed |
|---|---|---|---:|---:|---:|---|---:|---:|---:|
| Chattogram | 20-15-16 | 50003 | 3,230,507 | 3,227,246 | 15 | 41 (1–41) | 55 | 301 | 74 |
| Cumilla | 20-19-50 | 50009 | 440,233 | 439,414 | 2 | 27 (1–27) | 27 | 114 | 86 |

**Chattogram City Corporation:**
- Thanas: Akbarshah, Bayejid Bostami, Bakalia, Chalk Bazar, Chandgaon, Chattogram Port, Doublemooring, Epz,
  Halishahar, Kotwali, Khulshi, Pahartali, Panchlaish, Patenga, Sadarghat.
- 13 wards appear under two or three thanas: 06, 07, 08, 10, 11, 15, 16, 17, 24, 28, 31, 33 and 35. Only 08, 15, 24
  and 28 are printed with "(Part)". `ward_count` facts count distinct ward codes (41).
- C-01 has no unions inside the city corporation.

**Cumilla City Corporation:**
- Thanas: Adarsha Sadar Thana (18 wards) and Sadar Dakkhin Thana (9 wards).
- These thanas reuse the codes 67 and 33 of the Adarsha Sadar and Sadar Dakkhin upazilas. They are kept apart by
  the city-corporation code (the same handling as Narayanganj).

Ward numbers repeat between the two city corporations and with paurashava wards. Always use the full geocode.

## Hill districts (Rangamati, Khagrachhari, Bandarban)

BBS lists them with the same unit types as other districts (upazila → paurashava/union → mauza → village), and
nothing else:
- Rangamati: 10 upazilas; 2 paurashavas (Rangamati, Baghaichhari); 50 unions; 173 mauzas; 2,057 villages.
- Khagrachhari: 9 upazilas; 3 paurashavas (Khagrachhari, Matiranga, Ramgarh); 38 unions; 124 mauzas; 1,874 villages.
- Bandarban: 7 upazilas; 2 paurashavas (Bandarban, Lama); 34 unions; 96 (Key Findings) / 95 (D01) mauzas;
  2,139 villages.

None of these tables mention hill district councils, the regional council or circles; nothing about them is recorded here.

## Printed vs derived counts (conflicts inside BBS)

- **Upazilas, paurashavas, paura wards, population:** Key Findings, D01 and derived counts agree in every district.
- **Unions:** all agree except Cumilla: Key Findings 194 vs D01 193 = derived 193. The difference is probably the
  cantonment, as in Dhaka; BBS does not say.
- **Villages:** all agree except Cumilla: Key Findings 3,561 vs D01 3,531 = derived 3,531.
- **Mahallas:** Chattogram's Key Findings prints City Mahalla 301 and Mahalla 293 on separate lines. 301 + 293 = 594
  = D01 = derived, so no Key Findings mahalla fact is kept for Chattogram. The other districts agree.
- **City wards:** Chattogram Key Findings 41 vs D01 55 (D01 counts ward rows, split wards once per thana).
  Cumilla 27 in both.
- **Mauzas:** derived counts differ (split mauzas are counted per upazila; depopulated mauzas have no row). Use the
  printed totals. Two districts' printed totals disagree with each other:

  | District | KF | D01 | Derived | District | KF | D01 | Derived |
  |---|---:|---:|---:|---|---:|---:|---:|
  | Chattogram | 1,013 | 1,013 | 985 | Cumilla | 2,628 | 2,628 | 2,663 |
  | Cox's Bazar | 187 | 187 | 193 | Chandpur | 1,042 | 1,042 | 1,024 |
  | Bandarban | **96** | **95** | 102 | Brahmanbaria | 959 | 959 | 933 |
  | Rangamati | 173 | 173 | 174 | Khagrachhari | 124 | 124 | 127 |
  | Noakhali | 969 | 969 | 964 | Lakshmipur | **533** | **474** | 502 |
  | Feni | 543 | 543 | 558 | | | | |
- **Households:** D01 includes floating households, so it is slightly higher than C-01.

## Basis and seed comparison

Population is the final enumerated count incl. floating population, not PEC-adjusted. Division enumerated total (D01):
33,202,357. The seed district `population_2022` (`CITYPOP_ADJ`, "adjusted") equals BBS enumerated × 1.02940 for every
district (seed division 34,178,612). It is a proportional figure computed by the aggregator, not a BBS figure.

| District | Seed (CITYPOP_ADJ) | BBS enumerated | Seed area km² | BBS area km² (Key Findings) |
|---|---:|---:|---:|---:|
| Cumilla | 6,394,875 | 6,212,216 | 3095.4 | 3146.30 |
| Feni | 1,697,379 | 1,648,896 | 909.4 | 928.34 |
| Brahmanbaria | 3,403,786 | 3,306,563 | 1927.1 | 1881.20 |
| Rangamati | 666,627 | 647,586 | 5777.4 | 6116.11 |
| Noakhali | 3,732,042 | 3,625,442 | 2685.1 | 3685.87 |
| Chandpur | 2,713,247 | 2,635,748 | 1471.9 | 1645.32 |
| Lakshmipur | 1,994,930 | 1,937,948 | 1246.0 | 1440.39 |
| Chattogram | 9,439,076 | 9,169,465 | 4462.8 | 5282.92 |
| Cox's Bazar | 2,906,281 | 2,823,268 | 2179.1 | 2491.85 |
| Khagrachhari | 735,116 | 714,119 | 2862.8 | 2749.16 |
| Bandarban | 495,252 | 481,106 | 4607.2 | 4479.03 |

The seed areas are computed from polygons. The BBS figures include water and coastal/char areas, hence the large gaps
for Noakhali, Chandpur, Lakshmipur and Chattogram. The seed has no Chattogram Division pourashavas (BBS 62).

## Unions vs the seed (BBS 959 vs seed 950), per upazila where the count differs

Name-matched with the HDX matcher (direction words read as North/South/East/West); spelling-only differences are not
listed.

| Upazila | BBS | Seed | Difference |
|---|---:|---:|---|
| Burichang | 9 | 8 | Bharella Dakshin/Uttar (BBS) vs Varella (seed) |
| Chauddagram | 13 | 12 | Ujirpur only in BBS |
| Sadar Dakkhin / Lalmai | 7 / 9 | 14 / 8 | The seed lists Bagmara, Bhuloin, Belgor and Perul (North/South) under both Lalmai and Sadarsouth (duplicates); Galiara Dakkhin/Uttar (BBS) vs Goliara (seed); Bakai Uttar only in BBS |
| Laksam | 8 | 7 | Mudafarganj Dakkhin/Uttar (BBS) vs Mudafargonj (seed) |
| Nangalkot | 16 | 12 | Adra, Jodda and Raykot are split into Dakkhin/Uttar (Purba/Pashchim) in BBS; Battali only in BBS |
| Hajiganj | 12 | 11 | Dwadashgram only in BBS |
| Lakshmipur Sadar | 21 | 20 | Char Ramani, Mandari, Uttar Joypur (BBS) vs Nourthjoypur, Charramoni Mohon (seed) |
| Patiya / Karnaphuli | 17 / 5 | 22 / 5 | The seed lists Char Patharghata, Char Lakshya, Juldha, Bara Uthan and Sikalbaha under both Patiya and Karnafuli (duplicates); BBS has them only in Karnaphuli |
| Boalkhali | 9 | 10 | Purba Gomdandi only in seed |
| Hathazari | 14 | 15 | seed "Hathazari" union not in BBS |
| Rangunia | 15 | 14 | Chandraghona Kadamtali, Padua, Rangunia (BBS) vs Swanirbor Rangunia, Chandraghona (seed) |
| Sandwip / Satkania | 15 / 17 | 14 / 16 | Dirghapar, Dharmapur only in BBS |
| Chakaria | 18 | 16 | Lakkhyarchar, Purba Bara Bheola only in BBS |
| Cox's Bazar Sadar / Eidgaon | 5 / 5 | 10 / 0 | BBS puts Eidgaon, Islamabad, Islampur, Jalalabad and Pokkhali under the new Eidgaon upazila; the seed keeps them under Cox's Bazar Sadar |
| Guimara / Matiranga / Ramgarh / Mahalchhari / Khagrachhari Sadar | 3 / 7 / 2 / 4 / 5 | 0 / 8 / 3 / 5 / 4 | BBS puts Guimara, Hafchhari and Sindukchhari under Guimara upazila (seed: under Matiranga, Ramgarh, Mahalchhari); Bhaibonchhara under Khagrachhari Sadar (seed: Mahalchhari) |
| Panchhari | 5 | 4 | Ultachhari only in BBS |
| Belaichhari | 4 | 3 | Barathali only in BBS |
| Hatiya | 11 | 9 | Chanandi, Harni only in BBS |
| Alikadam | 4 | 2 | Kurukpata, Nayapara only in BBS |
| Bandarban Sadar | 6 | 5 | Jamchhari only in BBS |

These are census-frame counts as of mid-2022; later gazette changes are not reflected.

## Licence
No licence is stated on bbs.gov.bd. Facts only (names, codes, counts) are copied; attribution "Bangladesh Bureau of
Statistics, Population and Housing Census 2022".
