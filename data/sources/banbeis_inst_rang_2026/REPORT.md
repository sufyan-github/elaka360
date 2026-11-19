# BANBEIS institution lists (e-survey 2024) — Rangpur Division

- **Source:** the same 7 national XLSX lists on banbeis.gov.bd `/pages/files/` as for Rajshahi: school; college and school & college; madrasa; government technical; independent technical; universities; professional.
- **Method:** the Rajshahi collector, run as `python3 ../banbeis_inst_raj_2026/fetch.py --division rangpur` (accessed 2026-11-17). It keeps `DIVISION_NAME=Rangpur` and removes duplicate EIINs: 5,703 raw rows become 5,661 institutions. `raw/` holds the filtered CSVs (1.2 MB). Per-row `source_url` is `institute-search.ieims.banbeis.gov.bd/details/<EIIN>`; its `/api/` is disallowed by robots.txt and was not crawled.
- **Licence:** none stated.

## Counts: 5,661 institutions

| District | Total | Secondary | College | Madrasa | Technical | Polytechnic | Training | Primary* | University | Medical** |
|---|---|---|---|---|---|---|---|---|---|---|
| Dinajpur | 1,191 | 668 | 138 | 297 | 58 | 9 | 7 | 13 | 1 | 0 |
| Rangpur | 929 | 470 | 135 | 249 | 54 | 10 | 8 | 0 | 2 | 1 |
| Gaibandha | 755 | 402 | 83 | 214 | 38 | 6 | 5 | 7 | 0 | 0 |
| Kurigram | 733 | 365 | 90 | 222 | 42 | 2 | 1 | 10 | 1 | 0 |
| Thakurgaon | 632 | 381 | 61 | 124 | 51 | 8 | 4 | 3 | 0 | 0 |
| Nilphamari | 583 | 282 | 97 | 146 | 46 | 3 | 0 | 6 | 1 | 2 |
| Panchagarh | 439 | 289 | 41 | 78 | 25 | 3 | 0 | 2 | 0 | 1 |
| Lalmonirhat | 399 | 206 | 60 | 81 | 40 | 4 | 1 | 7 | 0 | 0 |

\* "Govt. Primary (pre to Eight)". \*\* Homeopathic colleges.

Totals by category: 3,063 secondary, 1,411 madrasa, 705 college, 354 technical, 48 primary, 45 polytechnic, 26 training, 5 university and 4 medical.

Rangpur District by upazila: Rangpur Sadar 190, Pirganj 186, Mithapukur 174, Pirgachha 111, Badarganj 93, Gangachara 72, Kaunia 64, Taraganj 39. The lists give no metropolitan thanas: the city is inside Rangpur Sadar.

`facts.csv` has 374 count rows.

Ownership:

| Ownership | Institutions |
|---|---|
| Non-government | 5,339 |
| Government | 243 |
| Autonomous | 32 |
| Local government | 17 |
| Christian missionary | 17 |
| Other | 7 |
| Cantonment board | 5 |
| NGO | 1 |

## Mapping and fields

The category mapping, `extra_json` and e-mail rules are the same as for Rajshahi; see `../banbeis_inst_raj_2026/REPORT.md`.

District and thana names are normalised to standard spellings, and the original is kept in `district_src` and `thana_src`. For example, "Nilphamari Sadar Upaz" becomes "Nilphamari Sadar". All 5,661 rows were normalised. Kurigram's upazila is written "Phulbari" and Dinajpur's "Fulbari".

There are no phones, coordinates or Bangla names. E-mails were kept for 4,356 rows by the same heuristic as for Rajshahi: the address has the institution's own domain, contains the EIIN, or contains an institution word. Placeholders, shared addresses and personal-looking addresses were dropped; a few personal ones may remain.

## Gaps

- There is no education-board cross-check. Rangpur Division is under the Dinajpur Education Board, which was not collected, so `rajshahi_board_listed` is absent.
- Government MBBS medical colleges are not in these lists. They are covered by the DGME and DGHS sources.

## Data quality

- English names are in upper case and contain typos, which were not corrected.
- Some education levels are wrong.
- 5 rows have no MPO value.
- Thanas are self-reported.

## Pilot matches

- Begum Rokeya University EIIN 136613 (Rangpur Sadar).
- Hajee Mohammad Danesh Science and Technology University EIIN 136622 (Dinajpur Sadar).
- Govt. Begum Rokeya College EIIN 127485.
- Carmichael Collegiate School and College EIIN 127510.
