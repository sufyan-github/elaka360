# BANBEIS institution lists (e-survey 2024) — Sylhet Division

- **Source:** the same 7 national XLSX lists on banbeis.gov.bd `/pages/files/` as for the earlier divisions: school; college and school & college; madrasa; government technical; independent technical; universities; professional.
- **Method:** the Rajshahi collector, run as `python3 ../banbeis_inst_raj_2026/fetch.py --division sylhet` (accessed 2026-11-18), then rebuilt with `--offline` after the Sylhet spellings were added.
  - It keeps `DIVISION_NAME=Sylhet` (all rows) and removes duplicate EIINs: 1,789 raw rows become 1,769 institutions.
  - `raw/` holds the filtered CSVs (0.4 MB).
  - Per-row `source_url` is `institute-search.ieims.banbeis.gov.bd/details/<EIIN>`; its `/api/` is disallowed by robots.txt and was not crawled.
  - A failed list download stops the run without writing outputs (none failed).
  - No file is near 20 MB (`places.csv` 1.1 MB).
- **Licence:** none stated.

## Counts: 1,769 institutions

| District | Total | Secondary | College | Madrasa | Technical | Polytechnic | Training | Primary* | University | Medical** |
|---|---|---|---|---|---|---|---|---|---|---|
| Sylhet | 694 | 333 | 150 | 163 | 23 | 1 | 2 | 13 | 7 | 2 |
| Sunamganj | 414 | 227 | 61 | 93 | 6 | 1 | 0 | 25 | 1 | 0 |
| Moulvibazar | 347 | 201 | 50 | 78 | 4 | 1 | 2 | 11 | 0 | 0 |
| Habiganj | 314 | 168 | 51 | 67 | 6 | 1 | 2 | 18 | 1 | 0 |

\* "Govt. Primary (pre to Eight)". \*\* Govt. Unani & Ayurvedic Medical College & Hospital, Sylhet (EIIN 133384) and Jalalabad Homoeopathic Medical College and Hospital (EIIN 133377), both Sylhet Sadar. The unchanged name rule puts both under `education.medical_college`.

Totals by category: 929 secondary, 401 madrasa, 312 college, 67 primary, 39 technical, 9 university, 6 training, 4 polytechnic, 2 medical. Coordinates: none (the lists have none).

Universities (9):
- Sylhet Sadar: Shahjalal University of Science and Technology (EIIN 136620), Sylhet Agricultural University (136607), Leading University, Metropolitan University, Sylhet International University, RTM Al Kabir Technical University.
- North East University Bangladesh (136696, Golapganj).
- Hobiganj Agricultural University (140212, Habiganj Sadar).
- Sunamganj Science and Technology University (139808, Sunamganj Sadar).

Sylhet District by upazila: Sylhet Sadar 153, Golapganj 72, Beanibazar 67, Bishwanath 53, Dakshin Surma 53, Gowainghat 53, Zakiganj 53, Kanaighat 45, Osmaninagar 38, Jaintiapur 33, Companiganj 26, Balaganj 25, Fenchuganj 23. `facts.csv` has 223 count rows.

Ownership: non-government 1,530 · government 189 · autonomous 24 · Christian missionary 11 · local government 7 · other 5 · NGO 2 · cantonment board 1.

## Mapping and fields

Category mapping, `extra_json` and e-mail rules as for Rajshahi (see `../banbeis_inst_raj_2026/REPORT.md`). District and thana names are normalised (original in `district_src`, `thana_src`); all 1,769 rows are normalised.
- District change: "Maulvibazar" → Moulvibazar (347 rows).
- Thana changes: "Beani Bazar" → Beanibazar (67), "Maulvibazar Sadar" → Moulvibazar Sadar (63), "Dharampasha" → Dharmapasha (31), "Sulla" → Shalla (20), "SHAYESTAGANJ" → Shayestaganj (9).
- One interpretive mapping: "Dakshin Sunamganj" (30 rows) is the former name of Shantiganj. It is mapped to Shantiganj with the note "source unit 'Dakshin Sunamganj' mapped to Shantiganj (the upazila's current name, Dakshin Sunamganj its former name)".
- The lists have no Madhyanagar unit (the newer upazila split from Dharmapasha); its institutions are probably under Dharmapasha.

**Sylhet city:** the lists have no Sylhet Metropolitan Police thanas; no row has `admin_unit: metropolitan_thana`. The city lies in the Sylhet Sadar and Dakshin Surma units, which are kept as upazilas. The collector knows the SMP thanas Kotwali, Jalalabad, Airport, Shahparan and Moglabazar for later runs, only in Sylhet District (`METRO_DISTRICT`). Dakshin Surma is not treated as a thana, because it is also an upazila of Sylhet District. The lists do not name a city corporation.

Tea gardens: 3 institutions have "tea garden" or "tea" in the name (e.g. Barmachora Tea Garden Government School and College); they are kept as listed.

No phones, coordinates or Bangla names. E-mails kept for 1,377 rows by the same heuristic as before (own domain, contains the EIIN, or an institution word). Placeholders, shared and personal-looking addresses are dropped; a few personal ones may remain.

## Gaps

- No education-board cross-check (`rajshahi_board_listed` absent); the Sylhet Education Board list was not collected.
- EIIN institutions only: kindergartens and English-medium schools without an EIIN are not in the lists.
- Government MBBS colleges (Sylhet MAG Osmani, Habiganj, Sunamganj) and Sylhet Medical University are not in the professional or university lists; they are covered by the DGME and DGHS sources.

## Data quality

Upper-case English names with typos (uncorrected, e.g. "SYLHET POLYTECHNIC INSTTTUTE, SYLHET", "MOULAVIBAZAR POLYTECHNIC INSTITUTE"). Some education levels are wrong and thanas are self-reported. 5 rows (the public universities) have no MPO value. 20 EIINs appear in both the government-technical and independent-technical lists (the first list wins; both are named in `banbeis_lists`).

## Pilot matches

Shahjalal University of Science and Technology EIIN 136620 · Govt. M. C. College EIIN 130457 (Sylhet Sadar) · Sylhet Govt. Pilot High School EIIN 130400 (Sylhet Sadar) · Govt. Jubilee High School EIIN 130023 (Sunamganj Sadar).
