# "দর্শনীয় স্থান" lists on district and upazila portals — Rangpur Division

- **Source:** `/pages/tourist-spot` (with `?page=N`) on the 8 district and 58 upazila portals of Rangpur Division (hosts verified by page title). Descriptions are not copied. Licence: none stated. Accessed 2026-11-17. Key PORTAL_TOURIST_SPOTS_RANG_2026.

## Counts: 317 rows

| District | Rows |
|---|---|
| Rangpur | 91 |
| Thakurgaon | 65 |
| Kurigram | 46 |
| Dinajpur | 39 |
| Panchagarh | 24 |
| Nilphamari | 19 |
| Gaibandha | 17 |
| Lalmonirhat | 16 |

Rangpur by upazila: Pirganj 19, Rangpur Sadar 13, Badarganj 12, Mithapukur 9, Kaunia 8, Gangachara 7, Pirgachha 5, Taraganj 2, none 16.

Categories (keyword rules):

| Category | Rows |
|---|---|
| tourism | 81 |
| historical | 68 |
| religious_site | 64 |
| river_haor | 25 |
| park | 22 |
| natural | 22 |
| religious.mazar | 14 |
| archaeological | 13 |
| museum | 7 |
| education.college | 1 |

`facts.csv`: entries per portal (66 rows).

## Gaps and cleaning

- **No coordinates or phones.** 7 Google Maps links are kept in `extra_json` but not used. The "contact" field usually holds a UNO or OC number, or directions, so it is not copied.
- **Empty lists:** Atowari, Khansama, Fulchhari, Palashbari, Sundarganj.
- **Cleaning:**
  - Leading numbering and ", upazila" suffixes are stripped; the original title is in `extra_json`.
  - Locations over 120 characters are dropped.
- **Listed twice:** 49 rows appear on both the district portal and an upazila portal and are flagged "also listed on …".
- **Not places:** some entries are generic titles, such as "পুরার্কীতি" or "আনন্দ নগর". They are kept as listed, with category `tourism`.
