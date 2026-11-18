# "দর্শনীয় স্থান" lists on district and upazila portals — Sylhet Division

- **Source:** `/pages/tourist-spot` (with `?page=N`) on the 4 district and 41 upazila portals of Sylhet Division (hosts verified by page title). Descriptions are not copied. Licence: none stated. Accessed 2026-11-18. Key PORTAL_TOURIST_SPOTS_SYL_2026.
- **fetch.py:** Sylhet tables (districts, upazilas with verified subdomains, SMP thanas), a `sylhet` entry in `DIVISION_TABLES`, and the Let's Encrypt intermediates for Sylhet runs. No other change. Rajshahi output is unchanged (checked byte-identical).

## Counts: 171 rows

| District | Rows (district portal / upazila portals) |
|---|---|
| Moulvibazar | 47 (8 / 39) |
| Sunamganj | 47 (23 / 24) |
| Sylhet | 42 (15 / 27) |
| Habiganj | 35 (9 / 26) |

| Category (same keyword rules) | Rows |
|---|---|
| tourism | 63 |
| park | 37 |
| historical | 17 |
| river_haor | 16 |
| religious.mazar | 14 |
| religious_site | 12 |
| natural | 7 |
| archaeological | 3 |
| museum | 2 |

`facts.csv`: entries per portal (45 rows).

## Gaps and cleaning
- **Empty lists:** Kanaighat, Dakshin Surma, Madhabpur, Nabiganj, Shantiganj (South Sunamganj), Madhyanagar.
- No coordinates, phones or Google Maps links.
- **Cleaning:**
  - 15 titles cleaned (numbering and ", upazila" suffixes stripped; original in `extra_json`);
  - 21 long locations dropped;
  - on 36 district-portal rows the upazila is inferred from the text;
  - 27 rows are flagged "also listed on …".
- **Effect of the shared keyword rules:** tea gardens (12) fall into park ("বাগান"). Waterfalls (মাধবকুন্ড, হামহাম, পান্তুমাই) and Jaflong / Ratargul / Bisnakandi are plain `tourism`, because the rules have no tea_garden, waterfall or hill rule. Some entries are combined or generic (e.g. "জাফলং, রাতারগুল সোয়ামফরেস্ট, বিছনাকান্দি, পান্তুমাই ঝর্ণা", "নদ-নদী", "চা বাগান"); they are kept as listed.
