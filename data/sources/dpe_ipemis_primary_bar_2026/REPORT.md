# DPE IPEMIS public school directory — Barishal Division

- **Source:** ipemis.dpe.gov.bd/search-school (linked from dpe.gov.bd). No login; no robots.txt (404). Licence: none stated.
- **Method:** the Rajshahi collector, run as `python3 ../dpe_ipemis_primary_raj_2026/fetch.py --division barishal` with IPEMIS `divisionId=5` (6 districts), accessed 2026-11-18.
  - It reads `/load-lite-school-list` per district, 500 rows at a time, and `api.ipemis.dpe.gov.bd/api/school-stat-public` for division, district and upazila statistics.
  - Responses are cached in `.partial/` during a run so `--resume` can continue an interrupted run; the cache was removed on success. The run completed without API errors.
  - `raw/` holds the division JSON (4.8 MB); `places.csv` is 5.4 MB; nothing is split.
- **Scope:** government, newly nationalised and experimental primary schools only (no kindergartens, NGO schools or ebtedayee madrasas).

## Counts: 6,249 schools

All rows `education.primary_school`, ownership "government"; no coordinates. By type: 3,471 government, 2,772 newly nationalised, 6 experimental.

| District | Schools | Govt | Newly nationalised | Experimental | Teachers* | Students* |
|---|---|---|---|---|---|---|
| Barishal | 1,590 | 996 | 593 | 1 | 9,235 | 205,896 |
| Patuakhali | 1,235 | 617 | 617 | 1 | 6,416 | 148,901 |
| Bhola | 1,047 | 457 | 589 | 1 | 5,786 | 157,573 |
| Pirojpur | 992 | 624 | 367 | 1 | 5,026 | 93,659 |
| Barguna | 799 | 401 | 397 | 1 | 4,225 | 80,575 |
| Jhalokathi | 586 | 376 | 209 | 1 | 3,112 | 51,493 |

\* Official IPEMIS live statistic. Division: 6,249 schools, 33,800 teachers, 738,097 students. The official school counts match the listed rows for the division, every district and every one of the 42 upazila units.

Barishal District by upazila: Bakerganj 280, Mehendiganj 208, Barishal Sadar 202, Wazirpur 181, Muladi 139, Babuganj 134, Gaurnadi 131, Banaripara 126, Agailjhara 97, Hizla 92.

`facts.csv` has 335 rows: 245 official statistics (schools, government schools, experimental schools, teachers, students per division, district and upazila) and 90 counts of listed records by type.

## Fields and gaps

- Bangla and English names (English often abbreviated); address = union/ward, upazila, district in Bangla. `extra_json`: school code, IPEMIS id, type, union, cluster, teacher and student counts. No coordinates, phones or e-mails; head teachers' names and mobiles on the detail pages are deliberately not collected.
- Upazila names are normalised to standard spellings, with the original in `upazila_src`: BAKHERGONJ → Bakerganj, CHARFASHION → Char Fasson, MEHENDIGONJ → Mehendiganj, MOTHBARIA → Mathbaria, BARISAL SADAR → Barishal Sadar, GOLACHIPA → Galachipa, UZIRPUR → Wazirpur, KOLAPARA → Kalapara, SHORUPKATHI(NESARABA (truncated by the source) → Nesarabad, NOLCHHITI → Nalchity, MIRZAGONJ → Mirzaganj, BABUGONJ → Babuganj, GOURNADI → Gaurnadi, BANORIPARA → Banaripara, TOZUMUDDIN → Tazumuddin, KAUKHALI → Kawkhali. All 6,249 rows are normalised.
- One interpretive mapping: IPEMIS unit ZIANAGAR (Pirojpur, 69 schools) is the upazila's former name. It is mapped to Indurkani, the name used by BBS 2022, BANBEIS and HRIS, with the note "source unit ZIANAGAR mapped to Indurkani (the upazila's current name, Zianagar its former name)".
- **Barishal city:** IPEMIS has no separate city unit and no Barishal Metropolitan Police thana units; no row has `admin_unit: metropolitan_thana`. Its BARISAL SADAR unit includes the city: 78 of its 202 schools have a union/ward "বরিশাল সিটি কর্পো: ওয়ার্ড নং-…". The source does not name a city corporation otherwise. The collector knows the four BMP thanas for later runs, only in Barishal District.
- 19 Bangla names repeat within an upazila under different codes (38 rows). Live data: re-runs will differ.
