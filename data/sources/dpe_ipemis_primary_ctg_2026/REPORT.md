# DPE IPEMIS public school directory — Chattogram Division

- **Source:** ipemis.dpe.gov.bd/search-school (linked from dpe.gov.bd). No login; no robots.txt (404). Licence: none stated.
- **Method:** the Rajshahi collector, run as `python3 ../dpe_ipemis_primary_raj_2026/fetch.py --division chattogram` with IPEMIS `divisionId=4` (11 districts, ids 32–42), accessed 2026-11-17. It reads `/load-lite-school-list` per district, 500 rows at a time, and `api.ipemis.dpe.gov.bd/api/school-stat-public` for division, district and upazila statistics. Responses are cached in `.partial/` during a run so `--resume` can continue an interrupted run; the cache was removed on success. The run completed without API errors. `raw/` holds the division JSON (9.1 MB); `places.csv` 10.1 MB; nothing split.
- **Scope:** government, newly nationalised and experimental primary schools only (no kindergartens, NGO schools, ebtedayee madrasas or camp learning centres).

## Counts: 11,586 schools

All rows `education.primary_school`, ownership "government"; no coordinates. By type: 7,821 government, 3,753 newly nationalised, 12 experimental.

| District | Schools | Govt | Newly nationalised | Experimental | Teachers* | Students* |
|---|---|---|---|---|---|---|
| Chattogram | 2,271 | 1,696 | 573 | 2 | 14,785 | 444,836 |
| Cumilla | 2,108 | 1,392 | 715 | 1 | 13,617 | 395,157 |
| Noakhali | 1,254 | 810 | 443 | 1 | 7,358 | 187,710 |
| Chandpur | 1,157 | 826 | 330 | 1 | 7,291 | 194,866 |
| Brahmanbaria | 1,106 | 722 | 383 | 1 | 6,686 | 260,997 |
| Lakshmipur | 733 | 523 | 209 | 1 | 4,534 | 112,670 |
| Rangamati | 708 | 420 | 287 | 1 | 3,002 | 49,732 |
| Cox's Bazar | 659 | 424 | 234 | 1 | 4,236 | 147,592 |
| Khagrachhari | 594 | 335 | 258 | 1 | 3,101 | 59,277 |
| Feni | 560 | 427 | 132 | 1 | 3,359 | 74,618 |
| Bandarban | 436 | 246 | 189 | 1 | 2,178 | 43,067 |

\* official IPEMIS live statistic. Division: 11,586 schools, 70,147 teachers, 1,970,522 students. The official school counts match the listed rows for the division, every district and every upazila/thana unit.

Chattogram District by unit: Fatikchhari 229, Mirsharai 191, Raozan 181, Banshkhali 160, Patiya 153, Rangunia 150, Sandwip 150, Hathazari 149, Satkania 149, Anwara 110, Boalkhali 107, Lohagara 103, Sitakunda 98, Chandanaish 91, Karnaphuli 34; city units Chandgaon 45, Double Muring 44, Pachlaish 36, Bandar 32, Kotwali 30, Pahartali 29.

`facts.csv` has 855 rows: 620 official statistics (schools, teachers, students per division, district and upazila/thana unit) and 235 counts of listed records by type.

## Fields and gaps

- Bangla and English names (English often abbreviated); address = union/ward, upazila, district in Bangla; `extra_json`: school code, IPEMIS id, type, union, cluster, teacher and student counts. No coordinates, phones or e-mails; head teachers' names and mobiles on the detail pages are deliberately not collected.
- Upazila names normalised to standard spellings, original in `upazila_src` (e.g. MIRERSWARAI → Mirsharai, ROWZAN → Raozan, BASHKHALI → Banshkhali, DEBIDHAR → Debidwar, CHOWDDAGRAM → Chauddagram, MANOHARGONG → Monoharganj, LUXMIPUR SADAR → Lakshmipur Sadar, RAYPUR → Raipur, DAGONBHUIYA → Daganbhuiyan, NAIKHANGCHHARI → Naikhongchhari, BILAICHARI → Belaichhari). Interpretive mappings: MATLAB (listed next to MATLAB UTTAR) → Matlab Dakshin (113); COMILLA SADAR (listed next to SADAR DAKHIN and LALMAI) → Cumilla Adarsha Sadar (111); unit COX'S BAZAR → Cox's Bazar Sadar (66); EIDGAH → Eidgaon (39).
- **Chattogram city:** IPEMIS has 6 city thana units (Kotwali, Pachlaish, Double Muring, Chandgaon, Pahartali, Bandar). They are kept in `upazila_en` as given (case and spacing only: "DOUBLEMURING" → "Double Muring", "PACHLAISH" → "Pachlaish") with `admin_unit: metropolitan_thana` and a note (216 rows). CMP now has 16 thanas, so one IPEMIS unit may cover more than the CMP thana of that name; the source does not name a city corporation. Karnaphuli is an upazila and stays one. Cumilla city schools are under Cumilla Adarsha Sadar / Cumilla Sadar Dakshin.
- **Chandraganj (Lakshmipur):** IPEMIS lists CHANDRAGANJ (129 schools) as its own upazila unit. Chandraganj is a thana, not an upazila; kept as "Chandraganj" with `admin_unit: thana` and a note; the source gives no parent upazila.
- **Matamuhuri (Cox's Bazar):** IPEMIS lists MATAMUHURI (44 schools) as its own upazila unit. Its status could not be confirmed from the collected sources, so it is kept as given ("MATAMUHURI") with the note "upazila 'MATAMUHURI' not normalised".
- 35 Bangla names repeat within an upazila under different codes. Live data: re-runs will differ.
