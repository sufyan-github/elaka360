# BANBEIS institution lists (e-survey 2024) — Khulna Division

- **Source:** the same 7 national XLSX lists on banbeis.gov.bd `/pages/files/` as for the earlier divisions: school; college and school & college; madrasa; government technical; independent technical; universities; professional.
- **Method:** the Rajshahi collector, run as `python3 ../banbeis_inst_raj_2026/fetch.py --division khulna` (accessed 2026-11-18).
  - It keeps `DIVISION_NAME=Khulna` (all rows) and removes duplicate EIINs: 4,884 raw rows become 4,840 institutions.
  - `raw/` holds the filtered CSVs (1.1 MB).
  - Per-row `source_url` is `institute-search.ieims.banbeis.gov.bd/details/<EIIN>`; its `/api/` is disallowed by robots.txt and was not crawled.
  - A failed list download stops the run without writing outputs (none failed).
  - No file is near 20 MB (`places.csv` 3.1 MB).
- **Licence:** none stated.

## Counts: 4,840 institutions

| District | Total | Secondary | College | Madrasa | Technical | Polytechnic | Training | Primary* | University | Medical** |
|---|---|---|---|---|---|---|---|---|---|---|
| Jashore | 1,002 | 525 | 120 | 306 | 28 | 5 | 13 | 4 | 1 | 0 |
| Khulna | 725 | 403 | 107 | 127 | 41 | 8 | 23 | 8 | 6 | 2 |
| Satkhira | 641 | 314 | 76 | 210 | 20 | 5 | 11 | 4 | 0 | 1 |
| Bagerhat | 568 | 321 | 49 | 164 | 22 | 1 | 4 | 5 | 0 | 2 |
| Jhenaidah | 497 | 292 | 75 | 111 | 10 | 3 | 3 | 3 | 0 | 0 |
| Kushtia | 480 | 305 | 70 | 71 | 17 | 7 | 0 | 5 | 4 | 1 |
| Magura | 305 | 167 | 40 | 72 | 18 | 2 | 3 | 2 | 0 | 1 |
| Chuadanga | 227 | 141 | 27 | 39 | 9 | 2 | 4 | 4 | 1 | 0 |
| Narail | 211 | 132 | 27 | 44 | 7 | 0 | 0 | 1 | 0 | 0 |
| Meherpur | 184 | 124 | 19 | 26 | 11 | 0 | 0 | 3 | 1 | 0 |

\* "Govt. Primary (pre to Eight)". \*\* Four homeopathic colleges (Khulna, Bagerhat, Kushtia, Satkhira), two Unani or Unani-Ayurvedic colleges (Khulna Unani Medical College; Hafez Kari Abdus Salam Unani Ayurvedic Medical College, Bagerhat) and one Ayurvedic college (Profulla Singha, Magura). The unchanged name rule puts all seven under `education.medical_college`.

Totals by category: 2,724 secondary, 1,170 madrasa, 610 college, 183 technical, 61 training, 39 primary, 33 polytechnic, 13 university, 7 medical. Coordinates: none (the lists have none).

Khulna District: upazilas Dumuria 108, Paikgachha 93, Koyra 71, Dacope 57, Batiaghata 44, Rupsa 42, Terokhada 34, Phultala 28, Dighalia 23; the other 225 rows are in 5 Khulna Metropolitan Police thanas (Sonadanga 61, Khalishpur 56, Khulna Sadar 55, Khan Jahan Ali 28, Daulatpur 25). `facts.csv` has 417 count rows.

Ownership: non-government 4,496 · government 266 · autonomous 24 · Christian missionary 22 · local government 20 · other 7 · NGO 3 · cantonment board 2.

## Mapping and fields

Category mapping, `extra_json` and e-mail rules as for Rajshahi (see `../banbeis_inst_raj_2026/REPORT.md`). District and thana names are normalised (original in `district_src`, `thana_src`); all 4,840 rows are normalised. Changes: district "Norail" → Narail (211); thanas "Bagher Para" → Bagherpara, "Horinakunda" → Harinakunda, "Jiban Nagar" → Jibannagar, "Mujib Nagar" → Mujibnagar.

**Khulna city:** inside the city the thana field is a KMP thana. These are kept in `upazila_en` as the source spells them, with `admin_unit: metropolitan_thana` and the note "metropolitan thana of Khulna City, not an upazila" (225 rows). Daulatpur is also an upazila of Kushtia: only Khulna District's Daulatpur counts as a metro thana (collector setting `METRO_DISTRICT`); Kushtia's Daulatpur (120 rows) stays an upazila. The lists do not name a city corporation.

**Jashore:** the lists have no "Jashore Sadar" unit. Its institutions are listed under thana "Kotwali" (201 rows, e.g. Jashore University of Science and Technology), the police thana of Jashore town. This is kept as given ("Kotwali") with `admin_unit: thana` and the note "thana listed by the source as its own unit, not an upazila"; it was not mapped to Jashore Sadar.

No phones, coordinates or Bangla names. E-mails kept for 3,631 rows by the same heuristic as before (own domain, contains the EIIN, or an institution word); placeholders, shared and personal-looking addresses dropped — a few personal ones may remain.

## Gaps

- No education-board cross-check (`rajshahi_board_listed` absent); the Jashore Education Board list was not collected.
- EIIN institutions only: kindergartens and English-medium schools without an EIIN are not in the lists.
- Khulna University of Engineering & Technology (KUET) is not in the university list (13 universities; Khulna University, Islamic University, JUST and Khulna Agricultural University are).
- Government MBBS colleges are not in the professional list; they are covered by the DGME and DGHS sources.

## Data quality

Upper-case English names with typos (uncorrected, e.g. "KHULNA UNIANI MEDICAL COLLEGE", "KUSTIA ZILLA SCHOOL"). Some education levels are wrong and thanas are self-reported (e.g. Govt. B. L. College under Khulna Sadar). 11 rows have no MPO value. 44 EIINs appear in both the government-technical and independent-technical lists (first list wins, both named in `banbeis_lists`).

## Pilot matches

Khulna University EIIN 136592 (Batiaghata) · Islamic University EIIN 136593 (Kushtia Sadar) · Jessore University of Science and Technology EIIN 136629 (Kotwali, Jashore) · Govt. B. L. College EIIN 116954 · Khulna Zilla School and College EIIN 117135.
