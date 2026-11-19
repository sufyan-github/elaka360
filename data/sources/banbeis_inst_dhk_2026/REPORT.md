# BANBEIS institution lists (e-survey 2024) — Dhaka Division

- **Source:** the same 7 national XLSX lists on banbeis.gov.bd `/pages/files/` as for Rajshahi and Rangpur: school; college and school & college; madrasa; government technical; independent technical; universities; professional.
- **Method:** the Rajshahi collector, run as `python3 ../banbeis_inst_raj_2026/fetch.py --division dhaka` (accessed 2026-11-17). It keeps `DIVISION_NAME=Dhaka` and removes duplicate EIINs: 6,570 raw rows become 6,500 institutions. `raw/` holds the filtered CSVs (1.4 MB). Per-row `source_url` is `institute-search.ieims.banbeis.gov.bd/details/<EIIN>`; its `/api/` is disallowed by robots.txt and was not crawled. `--resume` skips lists an interrupted run already saved. No file is near 20 MB (`places.csv` 4.2 MB).
- **Scope check:** the lists' Dhaka Division is the present 13-district division; no Mymensingh Division district appears.
- **Licence:** none stated.

## Counts: 6,500 institutions

| District | Total | Secondary | College | Madrasa | Technical | Polytechnic | Training | Primary* | University | Medical** |
|---|---|---|---|---|---|---|---|---|---|---|
| Dhaka | 1,382 | 587 | 426 | 112 | 91 | 26 | 10 | 67 | 60 | 3 |
| Tangail | 927 | 501 | 110 | 225 | 52 | 3 | 12 | 21 | 1 | 2 |
| Gazipur | 858 | 483 | 119 | 181 | 39 | 6 | 5 | 18 | 7 | 0 |
| Kishoreganj | 540 | 263 | 71 | 149 | 29 | 2 | 4 | 17 | 3 | 2 |
| Narsingdi | 475 | 264 | 80 | 88 | 23 | 6 | 5 | 9 | 0 | 0 |
| Faridpur | 417 | 249 | 48 | 82 | 19 | 3 | 7 | 7 | 1 | 1 |
| Narayanganj | 344 | 190 | 58 | 69 | 16 | 1 | 2 | 4 | 3 | 1 |
| Gopalganj | 306 | 194 | 45 | 44 | 14 | 3 | 0 | 5 | 1 | 0 |
| Madaripur | 287 | 171 | 31 | 69 | 8 | 1 | 3 | 4 | 0 | 0 |
| Rajbari | 279 | 145 | 40 | 72 | 9 | 3 | 5 | 5 | 0 | 0 |
| Manikganj | 260 | 168 | 34 | 28 | 13 | 5 | 3 | 8 | 1 | 0 |
| Shariatpur | 217 | 116 | 33 | 57 | 4 | 1 | 1 | 4 | 1 | 0 |
| Munshiganj | 208 | 125 | 31 | 37 | 6 | 3 | 1 | 4 | 1 | 0 |

\* "Govt. Primary (pre to Eight)". \*\* Homeopathic colleges, plus Kumudini Women's Medical College (Tangail), President Abdul Hamid Medical College (Kishoreganj) and a row named "Nursing Institute Medical College for Women & Hospital" (Dhaka), which the unchanged name rule puts under `education.medical_college`.

Totals by category: 3,456 secondary, 1,213 madrasa, 1,126 college, 323 technical, 173 primary, 79 university, 63 polytechnic, 58 training, 9 medical. Coordinates: none (the lists have none).

Dhaka District: upazilas Savar 131, Keraniganj 70, Dhamrai 61, Nawabganj 57, Dohar 34; the other 1,029 rows are in 50 Dhaka Metropolitan Police thanas (e.g. Mohammadpur 58, Pallabi 54, Badda 50, Jatrabari 49, Mirpur 45, Khilgaon 42, Uttara 39). `facts.csv` has 833 count rows.

Ownership: non-government 5,739 · government 558 · autonomous 68 · Christian missionary 60 · local government 32 · other 31 · cantonment board 7 · NGO 4 · not given 1 (Gopladi Fazil Madrasah, EIIN 112319, management "None").

## Mapping and fields

Category mapping, `extra_json` and e-mail rules as for Rajshahi (see `../banbeis_inst_raj_2026/REPORT.md`). District and thana names normalised (original in `district_src`, `thana_src`); all 6,500 rows normalised.

**Dhaka city:** inside the city the thana field is a DMP thana (Adabor … Wari). These are kept in `upazila_en` as the source names them, only doubled spaces removed ("Uttara  Paschim" → "Uttara Paschim"; "Biman Bandar", "Tejgaon Ind. Area", "Sher-E-Bangla Nagar" unchanged), with `admin_unit: metropolitan_thana` and the note "metropolitan thana of Dhaka City, not an upazila" (1,029 rows). The lists do not say whether a thana is in Dhaka North or South. Gazipur and Narayanganj city institutions are under Gazipur Sadar / Narayanganj Sadar / Bandar (no metro thanas in the lists).

No phones, coordinates or Bangla names. E-mails kept for 4,834 rows by the same heuristic as before (own domain, contains the EIIN, or an institution word); placeholders, shared and personal-looking addresses dropped — a few personal ones may remain.

## Gaps

- No education-board cross-check (`rajshahi_board_listed` absent); the Dhaka Education Board list was not collected.
- EIIN institutions only: Dhaka city's many kindergartens and English-medium schools without an EIIN are not in the lists.
- Some major public universities are missing from the university list (University of Dhaka, Jagannath University, BSMMU); they are covered by the UGC source. Government MBBS colleges are covered by the DGME and DGHS sources.

## Data quality

Upper-case English names with typos (uncorrected); some education levels wrong; 30 rows without MPO value; thanas self-reported; 70 EIINs appear in both the government-technical and independent-technical lists (first list wins, both named in `banbeis_lists`).

## Pilot matches

Jahangirnagar University EIIN 136589 (Savar) · BUET EIIN 136618 (thana Shahbagh) · National University EIIN 136590 and Bangladesh Open University EIIN 136591 (Gazipur Sadar) · BAF Shaheen College Kurmitola EIIN 107859 (Cantonment).
