# DPE IPEMIS public school directory — Sylhet Division

- **Source:** ipemis.dpe.gov.bd/search-school (linked from dpe.gov.bd). No login; no robots.txt (404). Licence: none stated.
- **Method:** the Rajshahi collector, run as `python3 ../dpe_ipemis_primary_raj_2026/fetch.py --division sylhet` with IPEMIS `divisionId=6` (4 districts), accessed 2026-11-18.
  - It reads `/load-lite-school-list` per district, 500 rows at a time, and `api.ipemis.dpe.gov.bd/api/school-stat-public` for division, district and upazila statistics.
  - The first run hit connect timeouts on ipemis.dpe.gov.bd while listing Sylhet District and stopped without writing outputs.
  - It was re-run about 5 minutes later with `--resume`, which reused the cached responses of the other three districts and completed. The cache (`.partial/`) was removed on success.
  - `raw/` holds the division JSON (3.8 MB); `places.csv` is 4.3 MB; nothing is split.
- **Scope:** government, newly nationalised and experimental primary schools only (no kindergartens, NGO schools or ebtedayee madrasas).

## Counts: 5,058 schools

All rows `education.primary_school`, ownership "government"; no coordinates. By type: 3,502 government, 1,552 newly nationalised, 4 experimental.

| District | Schools | Govt | Newly nationalised | Experimental | Teachers* | Students* |
|---|---|---|---|---|---|---|
| Sylhet | 1,478 | 1,131 | 346 | 1 | 7,788 | 246,361 |
| Sunamganj | 1,476 | 898 | 577 | 1 | 7,016 | 216,598 |
| Habiganj | 1,053 | 757 | 295 | 1 | 5,658 | 177,898 |
| Moulvibazar | 1,051 | 716 | 334 | 1 | 5,381 | 148,917 |

\* Official IPEMIS live statistic. Division: 5,058 schools, 25,843 teachers, 789,774 students. The official school counts match the listed rows for the division, every district and every one of the 41 upazila units.

Sylhet District by upazila: Golapganj 180, Beanibazar 150, Gowainghat 136, Zakiganj 136, Bishwanath 133, Kanaighat 130, Sylhet Sadar 124, Dakshin Surma 118, Osmaninagar 110, Companiganj 73, Balaganj 72, Jaintiapur 72, Fenchuganj 44. Sunamganj has 12 units, incl. Madhyanagar (84 schools).

`facts.csv` has 316 rows: 230 official statistics (schools, government schools, experimental schools, teachers, students per division, district and upazila) and 86 counts of listed records by type.

## Fields and gaps

- Bangla and English names (English often abbreviated); address = union/ward, upazila, district in Bangla. `extra_json`: school code, IPEMIS id, type, union, cluster, teacher and student counts. No coordinates, phones or e-mails; head teachers' names and mobiles on the detail pages are deliberately not collected.
- District names normalised: SYLHET, SUNAMGONJ → Sunamganj, HOBIGONJ → Habiganj, MOULVIBAZAR → Moulvibazar.
- Upazila names are normalised to standard spellings, with the original in `upazila_src`: CHATAK → Chhatak, NABIGONJ → Nabiganj, GOLAPGONJ → Golapganj, BANICHANG → Baniachong, KAMALGONJ → Kamalganj, BARALAKHA → Barlekha, BIANIBAZAR → Beanibazar, GOAINGHAT → Gowainghat, JAKIGONJ → Zakiganj, SUNAMGONJ SADAR → Sunamganj Sadar, JAMALGONJ → Jamalganj, DAKHIN SURMA → Dakshin Surma, HABIGONJ SADAR → Habiganj Sadar, OSMANI NAGAR → Osmaninagar, DHARAMPASHA → Dharmapasha, SHANTIGONJ → Shantiganj, BISWAMBARPUR → Bishwambarpur, COMPANIGONJ → Companiganj, JAINTAPUR → Jaintiapur, AZMIRIGONJ → Ajmiriganj, FENCHUGONJ → Fenchuganj, SHAESTHAGONJ → Shayestaganj. The others change case only. All 5,058 rows are normalised; no interpretive mappings were needed.
- **Sylhet city:** IPEMIS has no separate city unit and no Sylhet Metropolitan Police thana units; no row has `admin_unit: metropolitan_thana`. 75 schools have a union/ward "সিলেট সিটি কর্পোরেশন ওয়ার্ড …": 52 in the SYLHET SADAR unit and 23 in DAKHIN SURMA. Dakshin Surma is kept as the upazila (also an SMP thana name). The source does not name a city corporation otherwise. The collector knows the SMP thanas for later runs, only in Sylhet District.
- Tea gardens: about 48 schools have "tea garden"/"চা বাগান" in their names (43 in Moulvibazar, 5 in Habiganj); they are kept as the directory lists them.
- 36 Bangla names repeat within an upazila under different codes (75 rows). Live data: re-runs will differ.
