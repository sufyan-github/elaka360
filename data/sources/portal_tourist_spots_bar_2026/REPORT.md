# "দর্শনীয় স্থান" lists on district and upazila portals — Barishal Division

- **Source:** `/pages/tourist-spot` (with `?page=N`) on the 6 district and 42 upazila portals of Barishal Division (hosts verified by page title; Barishal under barisal.gov.bd, Jhalokathi under jhalakathi.gov.bd). Descriptions are not copied. Licence: none stated. Accessed 2026-11-18. Key PORTAL_TOURIST_SPOTS_BAR_2026.
- **fetch.py:** Barishal tables (districts, upazilas with verified subdomains, BMP thanas) and a `barishal` entry in `DIVISION_TABLES`; no other change.

## Counts: 214 rows

| District | Rows |
|---|---|
| Jhalokathi | 48 |
| Barishal | 44 |
| Patuakhali | 43 |
| Barguna | 30 |
| Bhola | 26 |
| Pirojpur | 23 |

Barishal by upazila: Barishal Sadar 11, Babuganj 7, Gaurnadi 5, Agailjhara 4, Bakerganj 2, Banaripara 2, Hizla 2, Wazirpur 1, Mehendiganj 1, none 9 (district-portal entries).

| Category (keyword rules) | Rows |
|---|---|
| tourism | 64 |
| religious_site | 38 |
| historical | 30 |
| river_haor | 29 |
| park | 25 |
| natural | 11 |
| religious.mazar | 7 |
| archaeological | 5 |
| museum | 4 |
| education.university | 1 |

`facts.csv`: entries per portal (48 rows).

## Gaps and cleaning
- **No coordinates or phones.** No Google Maps links. The "contact" field is not copied.
- **Empty lists:** Bakerganj, Wazirpur, Mehendiganj, Muladi, Pirojpur Sadar, Mathbaria, Char Fasson.
- **Cleaning:**
  - leading numbering and ", upazila" suffixes stripped on 25 titles (original in `extra_json`);
  - 13 locations over 120 characters dropped;
  - on 60 district-portal rows the upazila is inferred from the title/location text.
- **Listed twice:** 22 rows appear on both the district portal and an upazila portal; they are flagged "also listed on …".
- **Keyword-rule false hits** (same rules as the other divisions): "গৌরনদী", "কেরানীপাড়া রাখাইনপল্লী" and "খেপুপাড়া ডপলার রাডার স্টেশন" fall into river_haor ("নদী"/"পাড়" substrings).
- Some entries are generic (উপজেলা পরিষদ চত্বর, বীজ বর্ধন খামার); they are kept as `tourism`.
- Launch ghats and river ports named here (বরিশাল নদী বন্দর, মঙ্গল শিকদার লঞ্চঘাট, আমুয়া ফেরীঘাট, দৌলতখান লঞ্চঘাট, হুলারহাট নদী বন্দর, বদনা তলী খেয়াঘাট) stay tourism rows; transport rows are in DISTRICT_PORTALS_TRANSPORT_BAR_2026.
