# "দর্শনীয় স্থান" lists on district and upazila portals — Khulna Division

- **Source:** `/pages/tourist-spot` (with `?page=N`) on the 10 district and 59 upazila portals of Khulna Division (hosts verified by page title; Jashore under jessore.gov.bd). Descriptions are not copied. Licence: none stated. Accessed 2026-11-18. Key PORTAL_TOURIST_SPOTS_KHL_2026.
- **fetch.py:** Khulna tables (districts, upazilas with HDX spellings and verified subdomains, KMP thanas) and a `khulna` entry in `DIVISION_TABLES`; no other change.

## Counts: 310 rows

| District | Rows |
|---|---|
| Satkhira | 48 |
| Jhenaidah | 44 |
| Khulna | 43 |
| Jashore | 39 |
| Bagerhat | 34 |
| Magura | 31 |
| Kushtia | 21 |
| Chuadanga | 20 |
| Meherpur | 19 |
| Narail | 11 |

Khulna by upazila: Paikgachha 11, Dighalia 6, Rupsa 5, Phultala 5, Koyra 4, Batiaghata 3, Dacope 3, Dumuria 1, Terokhada 1, none 4 (district-portal entries).

Categories (keyword rules):

| Category | Rows |
|---|---|
| tourism | 116 |
| religious_site | 61 |
| historical | 47 |
| park | 26 |
| religious.mazar | 24 |
| river_haor | 20 |
| natural | 10 |
| archaeological, museum | 2 each |
| education (university 1, college 1) | 2 |

`facts.csv`: entries per portal (69 rows).

## Gaps and cleaning
- **No coordinates or phones.** No Google Maps links on any row. The "contact" field is not copied.
- **Empty lists** (re-checked live): Bagharpara, Sharsha, Mujibnagar, Kushtia Sadar.
- **Cleaning:** leading numbering and ", upazila" suffixes are stripped on 25 titles (original title in `extra_json`); 10 locations over 120 characters are dropped. On 46 district-portal rows the upazila is inferred from the title/location text.
- **Listed twice:** 74 rows appear on both the district portal and an upazila portal and are flagged "also listed on …".
- Some entries are generic titles; they are kept with category `tourism`.
