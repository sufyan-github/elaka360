# BANBEIS institution lists (e-survey 2024) — Rajshahi Division

- **Source:** national XLSX lists on 7 banbeis.gov.bd `/pages/files/` pages (school; college and school & college; madrasa; government technical; independent technical; universities; professional). `fetch.py` keeps `DIVISION_NAME=Rajshahi` and removes duplicate EIINs; `raw/` holds the filtered CSVs (~1.2 MB). Per-row `source_url`: `institute-search.ieims.banbeis.gov.bd/details/<EIIN>` (its `/api/` is disallowed by robots.txt and was not crawled). Licence: none stated.

## Counts: 5,730 institutions

| District | Total | Secondary | College | Madrasa | Technical | Polytechnic | Training | Primary* | University | Medical** |
|---|---|---|---|---|---|---|---|---|---|---|
| Rajshahi | 1,063 | 541 | 181 | 192 | 110 | 9 | 18 | 6 | 5 | 1 |
| Bogura | 1,006 | 454 | 128 | 307 | 85 | 9 | 10 | 11 | 1 | 1 |
| Naogaon | 865 | 429 | 87 | 276 | 57 | 1 | 8 | 6 | 1 | 0 |
| Sirajganj | 774 | 373 | 113 | 201 | 67 | 8 | 1 | 9 | 2 | 0 |
| Pabna | 659 | 301 | 100 | 179 | 52 | 5 | 5 | 15 | 1 | 1 |
| Natore | 562 | 295 | 92 | 100 | 56 | 6 | 7 | 4 | 2 | 0 |
| Chapainawabganj | 468 | 242 | 61 | 131 | 25 | 3 | 4 | 1 | 1 | 0 |
| Joypurhat | 333 | 155 | 34 | 111 | 24 | 2 | 3 | 4 | 0 | 0 |

\* "Govt. Primary (pre to Eight)". \*\* Homeopathic and unani colleges.

Rajshahi District by upazila/thana: Bagmara 187, Tanore 106, Godagari 101, Paba 99, Charghat 97, Mohanpur 88, Boalia (metro) 86, Puthia 77, Durgapur 75, Bagha 74, Rajpara (metro) 38, Motihar (metro) 19, Shah Makhdum (metro) 16. `facts.csv`: 464 count rows.

## Mapping and fields

school → secondary_school (incl. junior secondary) · college / school & college → college · madrasa → madrasa · technical lists → polytechnic / training_center / technical · professional → college (law, art, Sanskrit) / training_center (nursing) / medical_college (homeo, unani). Ownership from the management field; EIIN, MPO and other attributes in `extra_json`. Metro thanas flagged `admin_unit: metropolitan_thana`; thana spellings normalised (original in `thana_src`).

No phones, coordinates or Bangla names. E-mails kept for 4,414 rows by heuristic (own domain, contains the EIIN, or an institution word); placeholders, shared and personal-looking addresses dropped — a few personal ones may remain.

## Cross-check

Rajshahi Education Board JSON (rajshahiboard.gov.bd/sonali/ins.php, 7,738 rows, EIIN + name): 3,614 of 3,625 BANBEIS schools/colleges listed (flag `rajshahi_board_listed`); 296 Board EIINs match no BANBEIS list.

## Data quality

Uppercase English names with typos (uncorrected); some levels wrong; 7 rows without MPO; thanas self-reported.

## Pilot matches

Rajshahi College EIIN 126490 · University of Rajshahi EIIN 136586 · RUET EIIN 136625 (thana given as Boalia).
