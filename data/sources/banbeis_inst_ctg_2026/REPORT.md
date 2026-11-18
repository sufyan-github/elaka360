# BANBEIS institution lists (e-survey 2024) — Chattogram Division

- **Source:** the same 7 national XLSX lists on banbeis.gov.bd `/pages/files/` as for Rajshahi, Rangpur and Dhaka: school; college and school & college; madrasa; government technical; independent technical; universities; professional.
- **Method:** the Rajshahi collector, run as `python3 ../banbeis_inst_raj_2026/fetch.py --division chattogram` (accessed 2026-11-17). It keeps `DIVISION_NAME=Chattogram` (the collector also accepts "Chittagong"; all rows say "Chattogram") and removes duplicate EIINs: 5,937 raw rows become 5,878 institutions. `raw/` holds the filtered CSVs (1.3 MB). Per-row `source_url` is `institute-search.ieims.banbeis.gov.bd/details/<EIIN>`; its `/api/` is disallowed by robots.txt and was not crawled. `--resume` skips lists an interrupted run already saved; from this division on, a failed list download stops the run without writing outputs. No file is near 20 MB (`places.csv` 3.8 MB).
- **Licence:** none stated.

## Counts: 5,878 institutions

| District | Total | Secondary | College | Madrasa | Technical | Polytechnic | Training | Primary* | University | Medical** |
|---|---|---|---|---|---|---|---|---|---|---|
| Chattogram | 1,393 | 746 | 209 | 342 | 34 | 13 | 6 | 27 | 15 | 1 |
| Cumilla | 1,229 | 588 | 172 | 385 | 39 | 12 | 4 | 24 | 4 | 1 |
| Noakhali | 593 | 319 | 60 | 183 | 14 | 0 | 5 | 11 | 1 | 0 |
| Chandpur | 571 | 272 | 72 | 203 | 8 | 2 | 3 | 10 | 1 | 0 |
| Brahmanbaria | 455 | 259 | 70 | 87 | 12 | 3 | 2 | 20 | 1 | 1 |
| Cox's Bazar | 423 | 219 | 35 | 144 | 8 | 2 | 2 | 12 | 1 | 0 |
| Lakshmipur | 389 | 180 | 43 | 143 | 9 | 2 | 1 | 9 | 0 | 2 |
| Feni | 372 | 189 | 42 | 121 | 5 | 6 | 0 | 8 | 1 | 0 |
| Rangamati | 194 | 138 | 24 | 14 | 4 | 1 | 2 | 10 | 1 | 0 |
| Khagrachhari | 169 | 112 | 20 | 20 | 6 | 1 | 1 | 9 | 0 | 0 |
| Bandarban | 90 | 54 | 14 | 10 | 4 | 0 | 1 | 6 | 1 | 0 |

\* "Govt. Primary (pre to Eight)". \*\* Four homeopathic colleges and one Unani college (Rawshan Jahan Eastern Medical College and Hospital Unani, Lakshmipur), which the unchanged name rule puts under `education.medical_college`.

Totals by category: 3,076 secondary, 1,652 madrasa, 761 college, 146 primary, 143 technical, 42 polytechnic, 27 training, 26 university, 5 medical. Coordinates: none (the lists have none).

Chattogram District: upazilas Fatikchhari 111, Raozan 95, Hathazari 93, Satkania 89, Mirsharai 85, Patiya 78, Rangunia 70, Lohagara 67, Banshkhali 62, Boalkhali 55, Chandanaish 54, Sandwip 48, Anwara 43, Karnaphuli 19; the other 355 rows are in 12 Chattogram Metropolitan Police thanas (Kotwali 67, Double Mooring 44, Panchlaish 43, Chandgaon 38, Khulshi 32, Pahartali 31, Bayejid Bostami 26, Chittagong Port 23, Halishahar 19, Bakalia 17, Patenga 14, Sadarghat 1). `facts.csv` has 663 count rows.

Ownership: non-government 5,161 · government 466 · autonomous 95 · local government 65 · Christian missionary 56 · other 26 · cantonment board 6 · NGO 2 · not given 1 (Beacon Model College, EIIN 136527).

## Mapping and fields

Category mapping, `extra_json` and e-mail rules as for Rajshahi (see `../banbeis_inst_raj_2026/REPORT.md`). District and thana names normalised (original in `district_src`, `thana_src`); all 5,878 rows normalised. Examples: district "Brahamanbaria" → Brahmanbaria, "Coxs Bazar" → Cox's Bazar; thanas "Banchharampur" → Bancharampur, "Roypur" → Raipur, "Anowara" → Anwara, "Comilla Adarsha Sadar" → Cumilla Adarsha Sadar, "Comilla Sadar Dakshin" → Cumilla Sadar Dakshin, "Manoharganj" → Monoharganj, "Haim Char" → Haimchar; Rangamati names cut off after 19 characters or carrying a union ("Belai Chhari  Upazi" → Belaichhari, "Jurai Chhari Upazil" → Jurachhari, "Rangamati Sadar  Up" → Rangamati Sadar, "Kawkhali (Betbunia)" → Kawkhali).

**Chattogram city:** inside the city the thana field is a CMP thana. These are kept in `upazila_en` as the source spells them (only case changed: "SADARGHAT" → "Sadarghat"; "Bayejid Bostami" and "Chittagong Port" unchanged), with `admin_unit: metropolitan_thana` and the note "metropolitan thana of Chattogram City, not an upazila" (355 rows). "Chittagong Port" is the source's name for the port (Bandar) thana. Karnaphuli is an upazila and stays one. Cumilla city institutions are under Cumilla Adarsha Sadar / Cumilla Sadar Dakshin (no metro thanas in the lists). The lists do not name a city corporation.

No phones, coordinates or Bangla names. E-mails kept for 4,491 rows by the same heuristic as before (own domain, contains the EIIN, or an institution word); placeholders, shared and personal-looking addresses dropped — a few personal ones may remain.

## Gaps

- No education-board cross-check (`rajshahi_board_listed` absent); the Chattogram and Cumilla Education Board lists were not collected.
- EIIN institutions only: kindergartens and English-medium schools without an EIIN are not in the lists. No camp learning centres (Rohingya camps) are listed.
- No unit for Eidgaon (Cox's Bazar): its institutions are presumably still listed under Cox's Bazar Sadar.
- Government MBBS colleges are not in the professional list; they are covered by the DGME and DGHS sources.

## Data quality

Upper-case English names with typos (uncorrected, e.g. "PORTCITY INERNATIONAL UNIVERSITY", "RANGMATI SCIENCE AND TECHNOLOGY UNIVERSITY"); some education levels wrong; 15 rows without MPO value; thanas self-reported; 59 EIINs appear in both the government-technical and independent-technical lists (first list wins, both named in `banbeis_lists`).

## Pilot matches

University of Chittagong ("CHITTAGONG UNIVERSITY") EIIN 136587 (Hathazari) · CUET EIIN 136627 (Raozan) · Comilla University EIIN 136597 (Cumilla Sadar Dakshin) · Govt. Chittagong College EIIN 104532 (Kotwali) · Comilla Victoria Govt. College EIIN 105822 (Cumilla Adarsha Sadar) · Noakhali Science and Technology University EIIN 136628.
