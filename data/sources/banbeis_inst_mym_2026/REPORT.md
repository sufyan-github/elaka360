# BANBEIS institution lists (e-survey 2024) — Mymensingh Division

- **Source:** the same 7 national XLSX lists on banbeis.gov.bd `/pages/files/` as for the earlier divisions: school; college and school & college; madrasa; government technical; independent technical; universities; professional.
- **Method:** the Rajshahi collector, run as `python3 ../banbeis_inst_raj_2026/fetch.py --division mymensingh` (accessed 2026-11-18), then rebuilt with `--offline` after the Mymensingh spellings were added.
  - It keeps `DIVISION_NAME=Mymensingh` (all rows) and removes duplicate EIINs: 2,827 raw rows become 2,807 institutions.
  - `raw/` holds the filtered CSVs (0.6 MB).
  - Per-row `source_url` is `institute-search.ieims.banbeis.gov.bd/details/<EIIN>`; its `/api/` is disallowed by robots.txt and was not crawled.
  - A failed list download stops the run without writing outputs (none failed).
  - No file is near 20 MB (`places.csv` 1.8 MB).
- **Licence:** none stated.

## Counts: 2,807 institutions

| District | Total | Secondary | College | Madrasa | Technical | Polytechnic | Training | Primary* | University | Medical** |
|---|---|---|---|---|---|---|---|---|---|---|
| Mymensingh | 1,255 | 631 | 155 | 382 | 60 | 3 | 7 | 12 | 2 | 3 |
| Jamalpur | 702 | 365 | 85 | 177 | 59 | 6 | 1 | 6 | 1 | 2 |
| Netrokona | 483 | 272 | 53 | 91 | 50 | 2 | 1 | 12 | 1 | 1 |
| Sherpur | 367 | 182 | 32 | 107 | 33 | 3 | 3 | 7 | 0 | 0 |

\* "Govt. Primary (pre to Eight)". \*\* Unani and homoeopathic colleges from the professional list. The unchanged name rule puts them under `education.medical_college`:
- Mymensingh District: Sheikh Md Ibrahim Khalil Mazampara Unani Medical College and Hospital (Gafargaon), Momenshahi Unani Medical College and Mymensinh Homeo Pathy Medical College & Hospital (both Mymensingh Sadar).
- Jamalpur District: Jamalpur Himiopathic Medical College (Jamalpur Sadar) and Sarishabari Homoeopathic Medical College and Hospital.
- Netrokona District: Netrakona Homoeo Pathic Medical College & Hospital (Netrokona Sadar).

Totals by category: 1,450 secondary, 757 madrasa, 325 college, 202 technical, 37 primary, 14 polytechnic, 12 training, 6 medical, 4 university. Coordinates: none (the lists have none).

Universities (4, names as in the 2024 list):
- Bangladesh Agricultural University (EIIN 136588, Mymensingh Sadar).
- Jatiya Kabi Kazi Nazrul Islam University (136599, Trishal).
- Sheikh Fazilatunnesa Mujib University (136713, Jamalpur Sadar).
- Sheikh Hasina University (139145, Netrokona Sadar).

Mymensingh District by upazila: Mymensingh Sadar 168, Gafargaon 159, Fulbaria 144, Trishal 124, Bhaluka 123, Nandail 87, Muktagacha 85, Tarakanda 73, Iswarganj 68, Gouripur 67, Phulpur 62, Haluaghat 59, Dhobaura 36. `facts.csv` has 229 count rows.

Ownership: non-government 2,579 · government 153 · local government 27 · Christian missionary 24 · autonomous 17 · other 5 · cantonment board 1 · NGO 1.

## Mapping and fields

Category mapping, `extra_json` and e-mail rules as for Rajshahi (see `../banbeis_inst_raj_2026/REPORT.md`). District and thana names are normalised to the seed's English names (original in `district_src`, `thana_src`); all 2,807 rows are normalised.
- District change: "Netrakona" → Netrokona (483 rows).
- Thana changes: "Gaffargaon" → Gafargaon (159), "Sarishabari Upazila" → Sarishabari (89), "Melandaha" → Melandah (88), "Muktagachha" → Muktagacha (85), "Dewanganj" → Dewangonj (74), "Ishwarganj" → Iswarganj (68), "Gauripur" → Gouripur (67), "Sreebardi" → Sreebordi (66), "Bakshiganj" → Bokshiganj (65), "Nakla" → Nokla (60), "Mohanganj" → Mohongonj (34).
- No interpretive mappings were needed. The lists already use Tarakanda.

**Mymensingh city:** the lists have no metropolitan-police thanas for Mymensingh; no row has `admin_unit: metropolitan_thana`. The city lies in the Mymensingh Sadar unit, which is kept as an upazila. The collector has no thana list or `METRO_DISTRICT` for this division. The lists do not name a city corporation.

No phones, coordinates or Bangla names. E-mails kept for 2,125 rows by the same heuristic as before (own domain, contains the EIIN, or an institution word). Placeholders, shared and personal-looking addresses are dropped; a few personal ones may remain.

## Gaps

- No education-board cross-check (`rajshahi_board_listed` absent); the Mymensingh Education Board list was not collected.
- EIIN institutions only: kindergartens and English-medium schools without an EIIN are not in the lists.
- The MBBS colleges (Mymensingh, Community Based, Jamalpur and Netrokona Medical Colleges) are not in the professional or university lists. The DGME and DGHS sources cover them.

## Data quality

Upper-case English names with typos (uncorrected, e.g. "SHERPUR POLYTECHNIC INSTTITUTE", "MYMENSINH HOMEO PATHY MEDICAL COLLEGE & HOSPITAL", "JAMALPUR HIMIOPATHIC MEDICAL COLLEGE"). Some education levels are wrong and thanas are self-reported. 3 rows have no MPO value. 20 EIINs appear in both the government-technical and independent-technical lists (the first list wins; both are named in `banbeis_lists`).

## Pilot matches

Ananda Mohan Govt. College EIIN 111911 (Mymensingh Sadar) · Mymensingh Zilla School EIIN 111829 (Mymensingh Sadar) · Jamalpur Zilla School EIIN 109873 (Jamalpur Sadar) · Netrakona Govt College EIIN 113194 (Netrokona Sadar).
