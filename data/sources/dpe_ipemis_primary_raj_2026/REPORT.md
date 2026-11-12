# DPE IPEMIS public school directory — Rajshahi Division

- **Source:** ipemis.dpe.gov.bd/search-school (linked from dpe.gov.bd). No login; no robots.txt (404). `fetch.py` calls the listing endpoint the page uses (`/load-lite-school-list`) per district, 500 rows at a time, plus `api.ipemis.dpe.gov.bd/api/school-stat-public` for statistics. `raw/` holds the division JSON (6.6 MB). Licence: none stated.
- **Scope:** government, newly nationalised and experimental primary schools only (no kindergartens, NGO schools or ebtedayee madrasas).

## Counts: 8,666 schools (education.primary_school, government)

By type: 4,991 government, 3,665 newly nationalised, 10 experimental. By district: Sirajganj 1,673 · Bogura 1,603 · Naogaon 1,375 · Pabna 1,138 · Rajshahi 1,058 · Natore 739 · Chapainawabganj 708 · Joypurhat 372.

Rajshahi by upazila: Bagmara 220, Godagari 165, Tanore 128, Puthia 90, Durgapur 83, Paba 83, Mohanpur 81, Bagha 74, Charghat 73, Boalia(Sadar) 61 — the last is the whole city corporation, flagged metropolitan. The official Rajshahi statistic (1,058 schools, 6,326 teachers, 172,893 students) matches the listed rows.

`facts.csv` (531 rows): official live statistics (schools, teachers, students per division, district, upazila) and counts of listed records.

## Fields and gaps

Bangla + English names (English often abbreviated); address = union/ward, upazila, district; `extra_json`: school code, IPEMIS id, type, union, cluster, teacher and student counts. No coordinates, phones or e-mails; head-teacher names and mobiles on detail pages deliberately not collected. Live data. 3 Bangla names repeat within an upazila with different codes.
