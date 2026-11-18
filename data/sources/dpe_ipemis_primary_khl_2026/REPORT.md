# DPE IPEMIS public school directory — Khulna Division

- **Source:** ipemis.dpe.gov.bd/search-school (linked from dpe.gov.bd). No login; no robots.txt (404). Licence: none stated.
- **Method:** the Rajshahi collector, run as `python3 ../dpe_ipemis_primary_raj_2026/fetch.py --division khulna` with IPEMIS `divisionId=2` (10 districts), accessed 2026-11-18.
  - It reads `/load-lite-school-list` per district, 500 rows at a time, and `api.ipemis.dpe.gov.bd/api/school-stat-public` for division, district and upazila statistics.
  - Responses are cached in `.partial/` during a run so `--resume` can continue an interrupted run; the cache was removed on success. The run completed without API errors.
  - `raw/` holds the division JSON (6.1 MB); `places.csv` is 6.9 MB; nothing is split.
- **Scope:** government, newly nationalised and experimental primary schools only (no kindergartens, NGO schools or ebtedayee madrasas).

## Counts: 8,175 schools

All rows `education.primary_school`, ownership "government"; no coordinates. By type: 4,425 government, 3,741 newly nationalised, 9 experimental.

| District | Schools | Govt | Newly nationalised | Experimental | Teachers* | Students* |
|---|---|---|---|---|---|---|
| Jashore | 1,290 | 678 | 611 | 1 | 7,459 | 197,127 |
| Bagerhat | 1,163 | 618 | 544 | 1 | 5,886 | 119,918 |
| Khulna | 1,160 | 643 | 516 | 1 | 6,589 | 143,367 |
| Satkhira | 1,095 | 635 | 459 | 1 | 6,331 | 157,679 |
| Jhenaidah | 908 | 417 | 490 | 1 | 5,108 | 140,863 |
| Kushtia | 806 | 437 | 368 | 1 | 4,631 | 147,876 |
| Magura | 503 | 275 | 227 | 1 | 2,894 | 74,721 |
| Narail | 495 | 293 | 202 | 0 | 2,634 | 64,247 |
| Chuadanga | 446 | 266 | 179 | 1 | 2,626 | 80,786 |
| Meherpur | 309 | 163 | 145 | 1 | 1,782 | 40,607 |

\* official IPEMIS live statistic. Division: 8,175 schools, 45,940 teachers, 1,167,191 students. The official school counts match the listed rows for the division, every district and every one of the 60 upazila/thana units.

Khulna District by unit: Dumuria 214, Paikgachha 167, Koyra 142, Dacope 119, Batiaghata 115, Terokhada 102, Rupsa 68, Phultala 56, Dighalia 50; city unit Khulna Sadar 127.

`facts.csv` has 484 rows: 355 official statistics (schools, teachers, students per division, district and upazila/thana unit) and 129 counts of listed records by type.

## Fields and gaps

- Bangla and English names (English often abbreviated); address = union/ward, upazila, district in Bangla; `extra_json`: school code, IPEMIS id, type, union, cluster, teacher and student counts. No coordinates, phones or e-mails; head teachers' names and mobiles on the detail pages are deliberately not collected.
- Upazila names normalised to standard spellings, original in `upazila_src`: MOROLGONJ → Morrelganj, JESSORE SADAR → Jashore Sadar, BAGHERHAT SADAR → Bagerhat Sadar, AVOYNAGAR → Abhaynagar, BAGARPARA → Bagherpara, CHOUGACHHA → Chaugachha, SOILKUPA → Shailkupa, MOHESHPUR → Maheshpur, COTCHANDPUR → Kotchandpur, KAYRA → Koyra, DAKOPE → Dacope, DIGHULIA → Dighalia, FULTALA → Phultala, RUPSHA → Rupsa, TERAKHADA → Terokhada, PAIKGACHA → Paikgachha, KHOKSHA → Khoksa, SHREEPUR → Sreepur, MOLLARHAT → Mollahat, JIBAN NAGAR → Jibannagar, ASHASHUNI → Assasuni, KOLAROA → Kalaroa, SHAMNAGAR → Shyamnagar, KALIGONJ → Kaliganj. All 8,175 rows normalised; no interpretive mappings were needed.
- **Khulna city:** IPEMIS has a single city unit, KHULNA SADAR (127 schools), and no units for the other KMP thanas (Sonadanga, Khalishpur, Daulatpur, Khan Jahan Ali …). It is kept in `upazila_en` as "Khulna Sadar" with `admin_unit: metropolitan_thana` and the note "IPEMIS unit KHULNA SADAR is its only unit inside Khulna city (metropolitan thana), not an upazila; it may cover more than the present KMP thana of that name". The source does not name a city corporation. Kushtia's DAULATPUR is an upazila and stays one (the metro-thana rule applies only in Khulna District).
- 37 Bangla names repeat within an upazila under different codes (74 rows). Live data: re-runs will differ.
