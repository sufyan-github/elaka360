# BBS Population and Housing Census 2022 — Barishal Division

Source key `BBS_CENSUS_2022_BARISHAL` · census · trust level 4 · accessed 2026-11-18 · collected by
`python3 -I data/sources/bbs_census_2022/fetch.py --division barishal` · division `barishal` · kind `bbs_census`.

## What was obtained

Same page as the earlier runs (<https://bbs.gov.bd/pages/static-pages/6922e073933eb65569e27220>), resolved on
2026-11-18 (exact URLs: `raw/resolved_urls.json`):

| Document | Used for |
|---|---|
| Community Report Excel per district (6), sheet **C-01** (Barguna: sheet `C01`) | every geocoded unit down to village/mahalla, households, population by sex, rural/urban |
| District Report PDFs (6; PDF creation dates 29 May – 11 Jun 2024, 280–488 pages) | Key Findings (PDF pages 25–27): unit counts, area, density |
| Union Statistics PDF (national, June 2025), Table D01, PDF page 65 | district unit counts, households, population |

Downloads ≈ 150 MB (not committed; `fetch.py --division barishal` rebuilds; `--offline` rebuilds from `raw/`).
Committed: `raw/c01_barishal_division.csv` (0.7 MB, 9,694 C-01 rows incl. 4,888 village/mahalla rows, as printed),
`raw/district_report_key_findings.txt`, `raw/union_statistics_D01.txt`, `raw/resolved_urls.json`. areas.csv 1.2 MB
(3,986 rows), facts.csv 1.4 MB (3,933 rows); same fact set, `basis` values and code scheme (`BBS_GEOCODE_2022`,
division prefix 10) as the earlier runs. No Bangla names in the source.

fetch.py changes for this run:
- Barishal district table (order of the Community Report list on the BBS page; District Series labels; geocodes checked
  against the first C-01 row of each Excel): Barishal 06, Bhola 09, Pirojpur 79, Patuakhali 78, Barguna 04,
  Jhalokathi 42.
- `COMMUNITY_LABELS`: the BBS page prints two Community Report labels differently from the District Series labels
  (`PATUAKHAL:` and `JHALAKHATI:` vs `PATUAKHALI` and `JHALOKATHI`). For these two districts only, the Community Report
  link is looked up under the printed label.
- C-01 header: spaces around "/" are ignored (Pirojpur prints `Village/ Mahalla`).
- C-01 sheet name: if a workbook has no sheet `C-01`, sheet `C01` is read, after checking that its title is
  "Table C-01" (Barguna).
- None of these changes the earlier divisions: their labels, headers and sheet names matched before and still match the same way.

Rajshahi/Rangpur/Dhaka/Chattogram/Khulna outputs are unchanged:
- Rajshahi, full run with no `--division` (live downloads) into a scratch `--out`: areas.csv, facts.csv and all four
  raw files byte-identical with the committed folder (including `raw/resolved_urls.json`).
- Rangpur/Dhaka/Chattogram/Khulna: URL resolution on the current listing page identical to the committed
  `raw/resolved_urls.json`; `--offline` rebuilds from the committed raw/ byte-identical.
- A second full Barishal run into a scratch folder gave byte-identical files.
- No difference came from a live source changing.

## Coverage

| District | Geocode | Population (enum.) | Households | Upazilas | City corp. / thanas | Paurashavas | Unions | Paura wards | City wards | Mauza rows |
|---|---|---:|---:|---:|---|---:|---:|---:|---:|---:|
| Barishal | 10-06 | 2,570,446 | 628,895 | 10 | 1 / 1 | 6 | 88 | 54 | 30 | 1,127 |
| Bhola | 10-09 | 1,932,518 | 449,018 | 7 | – | 5 | 70 | 48 | – | 365 |
| Pirojpur | 10-79 | 1,198,195 | 298,405 | 7 | – | 4 | 53 | 36 | – | 443 |
| Patuakhali | 10-78 | 1,727,254 | 424,616 | 8 | – | 5 | 77 | 45 | – | 609 |
| Barguna | 10-04 | 1,010,531 | 255,346 | 6 | – | 4 | 42 | 36 | – | 300 |
| Jhalokathi | 10-42 | 661,160 | 162,355 | 4 | – | 2 | 32 | 18 | – | 437 |
| **Division** | 10 | **9,100,104** | | **42** | **1 / 1** | **26** | **362** | **237** | **30** | **3,281** |

Division totals agree with the D01 division row: 1 city corporation, 1 metro thana, 30 city wards, 42 upazilas,
26 paurashavas, 237 paura wards, 362 unions. D01 also prints 3,134 mauzas, 727 mahallas and 4,161 villages.

**Non-union units in the Union/Ward column:** none.
- Every row in that column outside the city corporation and the paurashavas is printed "… Union" and has a union-range code.
- There are no 997 (forest) or 998 (cantonment) rows, and no forest range, char or cantonment unit is printed as a union.
- Unions named "Char …"/"Darichar …" (e.g. Char Kaua, Char Kukrimukri, Char Montaj, Pashchim Char Umed, Darichar Khajuria) are union parishads and stay level `union`.
- No unit above mauza level is marked "(Part)". 364 mauza rows are "(Part)": 261 under wards, 103 under unions.

## Barishal City Corporation (geocode 10-06-50, seed 50007 in Barishal district 20033)

- Population 419,484 (C-01; the District Report's "Population by Upazila" prints the same). The seed has 419,351
  (`WIKI_CC`, census).
- **1 metro thana:** Barishal Sadar Thana (10-06-50-51), holding all wards.
- **30 wards (Ward No. 01–30)**, one row each, none split. `ward_count` = 30, equal to the Key Findings "City Ward" 30
  and D01.
- 230 mahallas and 28 mauza codes; no unions inside the city corporation.
- The thana code 51 is also Barishal Sadar upazila's code (10-06-51, 10 unions, outside the city). City-ward codes 001–030
  repeat paura-ward numbers. Always use the full geocode (10-06-50-51-…).

## Printed vs derived counts (conflicts inside BBS)

- **Upazilas, paurashavas, paura wards, unions, villages, mahallas, population:** Key Findings, D01 and derived counts
  agree in every district.
- **Mauzas:** Key Findings = D01 in every district. The derived counts differ: split mauzas are counted per union/ward,
  and depopulated mauzas have no row. Use the printed totals: Barishal 1,109, Bhola 355, Pirojpur 411, Patuakhali 577,
  Barguna 262, Jhalokathi 420.
- **Households:** D01 includes floating households, so it is slightly higher than C-01.
- **Area:** the Key Findings and the English profile narrative agree where both are printed (Bhola, Pirojpur, Barguna,
  Jhalokathi); Barishal and Patuakhali have no narrative figure.
- Two printing slips that do not affect the extracted values:
  - The Barishal report's Key Findings page xiv carries the footer "District Report: Mymensingh".
  - In Bhola's Key Findings, urban male + female (402,051) do not add up to the urban total (534,341). Urban/rural splits are not taken from the Key Findings.

## Basis and seed comparison

Population is the final enumerated count incl. floating population, not PEC-adjusted. Division enumerated total (D01):
9,100,104. The seed district `population_2022` (`CITYPOP_ADJ`, "adjusted") equals BBS enumerated × 1.02480 for every
district (seed division 9,325,820). It is a proportional figure computed by the aggregator, not a BBS figure.

| District | Seed (CITYPOP_ADJ) | BBS enumerated | Seed area km² | BBS area km² (Key Findings) |
|---|---:|---:|---:|---:|
| Jhalokathi | 677,559 | 661,160 | 740.4 | 706.76 |
| Patuakhali | 1,770,096 | 1,727,254 | 2622.4 | 3221.31 |
| Pirojpur | 1,227,915 | 1,198,195 | 1272.9 | 1277.80 |
| Barishal | 2,634,203 | 2,570,446 | 2224.6 | 2784.52 |
| Bhola | 1,980,452 | 1,932,518 | 1951.0 | 3403.48 |
| Barguna | 1,035,596 | 1,010,531 | 1349.7 | 1831.31 |

The seed areas are computed from polygons. The BBS figures include rivers and coastal/char areas, hence the large gaps
for Bhola, Patuakhali, Barguna and Barishal. The seed has no Barishal Division pourashavas (BBS 26).

## Unions vs the seed (BBS 362 vs seed 348), per upazila where the count differs

Name-matched with the HDX matcher (direction words read as North/South/East/West); spelling-only differences are not
listed. Upazila pairs were checked against the seed's Bangla names.
- All pair by name (e.g. Hijla = Hizla হিজলা, Ujirpur = Wazirpur উজিরপুর, Kanthalia = Kathalia কাঠালিয়া, Borhanuddin = Borhan Sddin বোরহান উদ্দিন) except **Indurkani** (10-79-90).
- Indurkani is the seed's **Zianagar** (জিয়ানগর, 30245):
  - the seed's Bangla name is the upazila's former name;
  - HDX's 2020 point for the same upazila is named Zianagar;
  - the seed's three Zianagar unions (Balipara, Pattashi, Parerhat) are three of BBS Indurkani's five.

| Upazila (BBS) | BBS | Seed | Difference |
|---|---:|---:|---|
| Mehendiganj | 16 | 13 | Dakkhin Ulania, Uttar Ulania, Joynagar, Sreepur only in BBS; Ulania (উলানিয়া) only in the seed |
| Borhanuddin | 9 | 5 | Gangapur, Hasannagar, Sachra, Tobgi only in BBS |
| Charfasson | 21 | 19 | Ahammadpur, Omarpur only in BBS |
| Bhandaria | 6 | 7 | Vandaria Sadar (ভান্ডারিয়া সদর) only in the seed |
| Indurkani (seed Zianagar) | 5 | 3 | Chandipur, Indurkani only in BBS |
| Bauphal | 15 | 14 | Chandradwip only in BBS |
| Dashmina | 7 | 6 | Char Borhan only in BBS |
| Patuakhali Sadar | 14 | 12 | Bhuria, Moukaran only in BBS |
| Rangabali | 6 | 5 | Moudubi only in BBS |
| Amtali | 7 | 8 | Chotobogi (ছোটবগী) only in the seed (the seed also has Chhotabagi under Taltali) |

Pairs the matcher does not make, but which are the same union by the seed's Bangla name:
- Dehergati ~ Deherhoti (দেহেরগতি, Babuganj)
- Char Kaua ~ Charcowa (চরকাউয়া, Barishal Sadar)
- Shikarpur ~ Shikerpur Wazirpur (শিকারপুর উজিরপুর, Ujirpur)
- Nadmula Shialkathi ~ Nodmulla (নদমূলা শিয়ালকাঠী, Bhandaria)
- Baga ~ Boga (বগা, Bauphal)
- Chaora ~ Chowra (চাওড়া, Amtali)

Probably the same, but the seed's Bangla name is shorter:
- Chirapara Parsaturia ~ Chirapara (চিরাপাড়া, Kawkhali)
- Shariktala Dumirtala ~ Shariktola (শরিকতলা, Pirojpur Sadar)

Low-confidence matcher pairs to review: Gaila~Goila, Mehendiganj~Mehendigong, Adhykkha Nazrulnagar~Nazrulnagar,
Char Kukrimukri~Kukrimukri, Medua~Madua, Kaukhali~Kawkhali Sadar, Gulishakhali~Haltagulishakhali,
Atharogachhia~Athrogasia.

These are census-frame counts as of mid-2022; later gazette changes are not reflected.

## Licence
No licence is stated on bbs.gov.bd. Facts only (names, codes, counts) are copied; attribution "Bangladesh Bureau of
Statistics, Population and Housing Census 2022".
