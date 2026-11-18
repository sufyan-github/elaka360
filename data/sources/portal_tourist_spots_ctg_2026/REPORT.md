# "দর্শনীয় স্থান" lists on district and upazila portals — Chattogram Division

- **Source:** `/pages/tourist-spot` (with `?page=N`) on the 11 district and 104 upazila portals of Chattogram Division (hosts verified by page title). Descriptions are not copied. Licence: none stated. Accessed 2026-11-18. Key PORTAL_TOURIST_SPOTS_CTG_2026.
- **fetch.py:** Chattogram tables (districts, upazilas with HDX spellings and verified subdomains, CMP thanas) and a `chattogram` entry in `DIVISION_TABLES`; no other change.

## Counts: 567 rows

| District | Rows |
|---|---|
| Rangamati | 95 |
| Chattogram | 78 |
| Khagrachhari | 68 |
| Cumilla | 56 |
| Bandarban | 50 |
| Cox's Bazar | 49 |
| Brahmanbaria | 42 |
| Chandpur | 37 |
| Lakshmipur | 37 |
| Noakhali | 34 |
| Feni | 21 |

Chattogram by upazila: Hathazari 12, Sitakunda 7, Banshkhali 6, Chandanaish 6, Anwara 5, Mirsarai 5, others 1–4, none 13 (district-portal entries).

Categories (keyword rules):

| Category | Rows |
|---|---|
| tourism | 252 |
| religious_site | 73 |
| park | 65 |
| historical | 64 |
| river_haor | 37 |
| religious.mazar | 33 |
| natural | 23 |
| archaeological | 8 |
| museum | 7 |
| education (college 4, university 1) | 5 |

`facts.csv`: entries per portal (115 rows).

## Gaps and cleaning
- **No coordinates or phones.** No Google Maps links on any row. The "contact" field is not copied.
- **Empty lists:** Karnaphuli, Homna, Chhagalnaiya, Subarnachar, Ramganj, Eidgaon, Guimara.
- **Cleaning:** leading numbering and ", upazila" suffixes are stripped (original title in `extra_json`); 36 locations over 120 characters are dropped.
- **Listed twice:** 96 rows appear on both the district portal and an upazila portal and are flagged "also listed on …".
- Some entries are generic titles; they are kept with category `tourism`.
