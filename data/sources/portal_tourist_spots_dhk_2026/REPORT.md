# "দর্শনীয় স্থান" lists on district and upazila portals — Dhaka Division

- **Source:** `/pages/tourist-spot` (with `?page=N`) on the 13 district and 89 upazila portals of Dhaka Division (hosts verified by page title). Descriptions are not copied. Licence: none stated. Accessed 2026-11-17. Key PORTAL_TOURIST_SPOTS_DHK_2026.
- **fetch.py:** Dhaka tables (districts, upazilas with HDX spellings and verified subdomains, DMP thanas) and a `dhaka` entry in `DIVISION_TABLES`; no other change.

## Counts: 429 rows

| District | Rows |
|---|---|
| Kishoreganj | 71 |
| Tangail | 59 |
| Dhaka | 42 |
| Munshiganj | 42 |
| Shariatpur | 31 |
| Faridpur | 30 |
| Narayanganj | 27 |
| Narsingdi | 25 |
| Gopalganj | 25 |
| Madaripur | 24 |
| Rajbari | 20 |
| Manikganj | 19 |
| Gazipur | 14 |

Dhaka by upazila: Dhamrai 6, Nawabganj 5, Savar 5, Keraniganj 4, Dohar 2, none 20 (district-portal entries, mostly in Dhaka city).

Categories (keyword rules):

| Category | Rows |
|---|---|
| tourism | 126 |
| religious_site | 80 |
| historical | 72 |
| park | 43 |
| religious.mazar | 38 |
| river_haor | 36 |
| natural | 11 |
| museum | 8 |
| archaeological | 7 |
| education (university 4, college 3, medical college 1) | 8 |

`facts.csv`: entries per portal (102 rows).

## Gaps and cleaning
- **No coordinates or phones.** 9 Google Maps links are kept in `extra_json` but not used. The "contact" field (UNO/OC numbers or directions) is not copied.
- **Empty lists:** Alfadanga, Bhanga, Sadarpur (Faridpur).
- **Cleaning:** leading numbering and ", upazila" suffixes are stripped (original title in `extra_json`); 26 locations over 120 characters are dropped. Shorter "locations" can be a sentence, kept as printed.
- **Listed twice:** 28 rows appear on both the district portal and an upazila portal and are flagged "also listed on …".
- Some entries are generic titles; they are kept with category `tourism`.
