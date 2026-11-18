# "দর্শনীয় স্থান" lists on district and upazila portals — Mymensingh Division

- **Source:** `/pages/tourist-spot` (with `?page=N`) on the 4 district and 35 upazila portals of Mymensingh Division (hosts verified by page title). Descriptions are not copied. Licence: none stated. Accessed 2026-11-18. Key PORTAL_TOURIST_SPOTS_MYM_2026.
- **fetch.py:** Mymensingh tables (districts, upazilas with the seed's spellings and verified subdomains, no metro thanas) and a `mymensingh` entry in `DIVISION_TABLES`. No other change. Rajshahi output is unchanged (checked byte-identical).

## Counts: 145 rows

| District | Rows (district portal / upazila portals) |
|---|---|
| Mymensingh | 55 (2 / 53; Haluaghat 15, Mymensingh Sadar 9, Dhobaura 6) |
| Netrokona | 43 (9 / 34) |
| Jamalpur | 27 (9 / 18) |
| Sherpur | 20 (8 / 12) |

| Category (same keyword rules) | Rows |
|---|---|
| tourism | 63 |
| historical | 18 |
| river_haor | 18 |
| religious.mazar | 16 |
| park | 12 |
| religious_site | 9 |
| natural | 6 |
| museum | 2 |
| education.university (জাতীয় কবি কাজী নজরুল ইসলাম বিশ্ববিদ্যালয়, Trishal) | 1 |

`facts.csv`: entries per portal (39 rows).

## Gaps and cleaning
- **Empty list:** Nalitabari.
- No coordinates or phones.
- **Cleaning:**
  - 18 titles cleaned (original in `extra_json`);
  - 9 long locations dropped;
  - on 18 rows the upazila is inferred from the text;
  - 20 rows are flagged "also listed on …".
- `upazila_en` is set on 135 rows.
- **Generic entries kept as listed:** "পর্যটন", "কলা বাগান", "রাবার ডেম", "পাতলা বন", "কংশ নদী", "যমুনা নদী".
