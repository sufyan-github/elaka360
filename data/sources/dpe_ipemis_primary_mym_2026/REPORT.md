# DPE IPEMIS public school directory — Mymensingh Division

- **Source:** ipemis.dpe.gov.bd/search-school (linked from dpe.gov.bd). No login; no robots.txt (404). Licence: none stated.
- **Method:** the Rajshahi collector, run as `python3 ../dpe_ipemis_primary_raj_2026/fetch.py --division mymensingh` with IPEMIS `divisionId=8` (4 districts), accessed 2026-11-18.
  - It reads `/load-lite-school-list` per district, 500 rows at a time, and `api.ipemis.dpe.gov.bd/api/school-stat-public` for division, district and upazila statistics.
  - The first run completed (5,364 schools) before the Mymensingh spellings were in the collector. Its live statistics therefore carried unnormalised names, which `--offline` would keep.
  - The collector was re-run online a few minutes later, after the spellings were added, and replaced all outputs. It again listed 5,364 schools. No request failed; the cache (`.partial/`) was removed on success.
  - `raw/` holds the division JSON (4.1 MB); `places.csv` is 4.6 MB; nothing is split.
- **Scope:** government, newly nationalised and experimental primary schools only (no kindergartens, NGO schools or ebtedayee madrasas).

## Counts: 5,364 schools

All rows `education.primary_school`, ownership "government"; no coordinates. By type: 2,934 government, 2,426 newly nationalised, 4 experimental.

| District | Schools | Govt | Newly nationalised | Experimental | Teachers* | Students* |
|---|---|---|---|---|---|---|
| Mymensingh | 2,141 | 1,299 | 841 | 1 | 12,207 | 361,591 |
| Netrokona | 1,316 | 661 | 654 | 1 | 7,087 | 187,202 |
| Jamalpur | 1,165 | 612 | 552 | 1 | 6,524 | 153,479 |
| Sherpur | 742 | 362 | 379 | 1 | 4,037 | 85,780 |

\* Official IPEMIS live statistic. Division: 5,364 schools, 29,855 teachers, 788,052 students. The official school counts match the listed rows for the division, every district and every one of the 35 upazila units.

Mymensingh District by upazila: Gafargaon 238, Fulbaria 201, Mymensingh Sadar 186, Trishal 181, Nandail 178, Gouripur 177, Haluaghat 165, Bhaluka 164, Muktagacha 161, Tarakanda 141, Iswarganj 140, Phulpur 119, Dhobaura 90.

`facts.csv` has 274 rows: 200 official statistics (schools, government schools, experimental schools, teachers, students per division, district and upazila) and 74 counts of listed records by type.

## Fields and gaps

- Bangla and English names (English often abbreviated); address = union/ward, upazila, district in Bangla. `extra_json`: school code, IPEMIS id, type, union, cluster, teacher and student counts. No coordinates, phones or e-mails; head teachers' names and mobiles on the detail pages are deliberately not collected.
- District names (MYMENSINGH, JAMALPUR, NETROKONA, SHERPUR) change case only.
- Upazila names are normalised to the seed's English spellings, with the original in `upazila_src`: GAFFARGAON → Gafargaon, MADARGONJ → Madarganj, MYMENSING SADAR → Mymensingh Sadar, KANDUA → Kendua, MUKTAGACHHA → Muktagacha, ISWARGONJ → Iswarganj, SHARISHABARI → Sarishabari, FULPUR → Phulpur, NAKLA → Nokla, BAKSHIGONJ → Bokshiganj, DHUBAURA → Dhobaura, MOHANGANJ → Mohongonj, KHALIAJHURI → Khaliajuri. The others (incl. DEWANGONJ, MELANDAH, SREEBORDI, GOURIPUR, TARAKANDA) change case only. All 5,364 rows are normalised; no interpretive mappings were needed.
- **Mymensingh city:** IPEMIS has no separate city unit and no metropolitan-police thana units for Mymensingh; no row has `admin_unit: metropolitan_thana`. 30 schools have a union/ward "ময়মনসিংহ সিটি কর্পোরেশন ওয়ার্ড …", all in the MYMENSING SADAR unit (kept as the upazila Mymensingh Sadar). The source does not name a city corporation otherwise. The collector has no thana list or `METRO_DISTRICT` for this division.
- 19 Bangla names repeat within an upazila under different codes (39 rows). Live data: re-runs will differ.
