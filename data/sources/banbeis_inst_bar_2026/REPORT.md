# BANBEIS institution lists (e-survey 2024) — Barishal Division

- **Source:** the same 7 national XLSX lists on banbeis.gov.bd `/pages/files/` as for the earlier divisions: school; college and school & college; madrasa; government technical; independent technical; universities; professional.
- **Method:** the Rajshahi collector, run as `python3 ../banbeis_inst_raj_2026/fetch.py --division barishal` (accessed 2026-11-18).
  - It keeps `DIVISION_NAME=Barishal` (all rows) and removes duplicate EIINs: 3,375 raw rows become 3,349 institutions.
  - `raw/` holds the filtered CSVs (0.7 MB).
  - Per-row `source_url` is `institute-search.ieims.banbeis.gov.bd/details/<EIIN>`; its `/api/` is disallowed by robots.txt and was not crawled.
  - A failed list download stops the run without writing outputs (none failed).
  - No file is near 20 MB (`places.csv` 2.2 MB).
- **Licence:** none stated.

## Counts: 3,349 institutions

| District | Total | Secondary | College | Madrasa | Technical | Polytechnic | Training | Primary* | University | Medical** |
|---|---|---|---|---|---|---|---|---|---|---|
| Barishal | 833 | 435 | 107 | 235 | 23 | 8 | 9 | 11 | 4 | 1 |
| Patuakhali | 680 | 297 | 68 | 266 | 29 | 7 | 4 | 8 | 1 | 0 |
| Bhola | 592 | 270 | 62 | 234 | 9 | 5 | 1 | 10 | 0 | 1 |
| Pirojpur | 517 | 269 | 52 | 172 | 19 | 1 | 3 | 0 | 1 | 0 |
| Barguna | 368 | 177 | 39 | 128 | 16 | 2 | 1 | 5 | 0 | 0 |
| Jhalokathi | 359 | 181 | 38 | 123 | 15 | 1 | 0 | 1 | 0 | 0 |

\* "Govt. Primary (pre to Eight)". \*\* Two homeopathic colleges: Apex Homeopathy Medical College and Hospital (Barishal Sadar, EIIN 133644) and Lions Homeopathy Medical College & Nolini Das Hospital (Bhola Sadar, EIIN 133410). The unchanged name rule puts both under `education.medical_college`.

Totals by category: 1,629 secondary, 1,158 madrasa, 366 college, 111 technical, 35 primary, 24 polytechnic, 18 training, 6 university, 2 medical. Coordinates: none (the lists have none).

Universities (6):
- University of Barisal (EIIN 136610), Global University Bangladesh, Trust University Barisal and University of Global Village, all in Barishal Sadar.
- Patuakhali Science and Technology University (EIIN 136621, Dumki).
- Bangabandhu Sheikh Mujibur Rahman Science and Technology University, Pirojpur (EIIN 140219, Pirojpur Sadar).

Barishal District by upazila: Barishal Sadar 182, Bakerganj 172, Wazirpur 88, Mehendiganj 75, Muladi 68, Babuganj 63, Banaripara 61, Gaurnadi 49, Agailjhara 44, Hizla 31. `facts.csv` has 258 count rows.

Ownership: non-government 3,139 · government 172 · Christian missionary 15 · local government 11 · other 7 · autonomous 4 · NGO 1.

## Mapping and fields

Category mapping, `extra_json` and e-mail rules as for Rajshahi (see `../banbeis_inst_raj_2026/REPORT.md`). District and thana names are normalised (original in `district_src`, `thana_src`); all 3,349 rows are normalised.
- District change: "Jhalokati" → Jhalokathi (359 rows).
- Thana changes: "Banari Para" → Banaripara, "Burhanuddin" → Borhanuddin, "Daulat Khan" → Daulatkhan, "Kala Para" → Kalapara, "Kanthalia" → Kathalia, "Jhalokati Sadar" → Jhalokathi Sadar, "Nesarabad (Swarupkati)" → Nesarabad, and the suffix "Upazila" dropped (Dumki, Mirzaganj, Nazirpur).

**Barishal city:** the lists have no Barishal Metropolitan Police thanas; no row has `admin_unit: metropolitan_thana`. The city is in the unit "Barisal Sadar (Kotwali)" (182 rows), which names both the Sadar upazila and Kotwali, the city's police thana. It is mapped to Barishal Sadar (`admin_unit: upazila`) with the note "source unit 'Barisal Sadar (Kotwali)' (Sadar upazila incl. Barishal city / Kotwali thana) mapped to Barishal Sadar". The collector knows the four BMP thanas (Kotwali, Airport, Kawnia, Bandar) for later runs, only in Barishal District (`METRO_DISTRICT`), as for Khulna. The lists do not name a city corporation.

No phones, coordinates or Bangla names. E-mails kept for 2,567 rows by the same heuristic as before (own domain, contains the EIIN, or an institution word). Placeholders, shared and personal-looking addresses are dropped; a few personal ones may remain.

## Gaps

- No education-board cross-check (`rajshahi_board_listed` absent); the Barishal Education Board list was not collected.
- EIIN institutions only: kindergartens and English-medium schools without an EIIN are not in the lists.
- Government MBBS colleges (Sher-e-Bangla Medical College, Patuakhali Medical College) are not in the professional list; they are covered by the DGME and DGHS sources.

## Data quality

Upper-case English names with typos (uncorrected, e.g. "BANGABANDHU SHEIKH MUJIBUR RAHMAN SCIENCE AND TECHNOLOGY UNIVERISTY PIROJPUR"). Some education levels are wrong and thanas are self-reported. 6 rows have no MPO value. 26 EIINs appear in both the government-technical and independent-technical lists (the first list wins; both are named in `banbeis_lists`).

## Pilot matches

University of Barisal EIIN 136610 · Patuakhali Science and Technology University EIIN 136621 (Dumki) · Barisal Zilla School EIIN 100742 (Barishal Sadar) · Barguna Zilla School EIIN 100154.
