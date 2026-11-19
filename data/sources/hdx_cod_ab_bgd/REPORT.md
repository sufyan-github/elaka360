# HDX COD-AB Bangladesh v03 — Rajshahi Division

- **Source:** https://data.humdata.org/dataset/cod-ab-bgd. Original source BBS; contributed by OCHA ROAP; published by OCHA FIS / HDX.
- **Licence:** CC BY-IGO 3.0.
- **Version:** v03, valid_on 2023-05-21, reviewed 2025-06-01, resource modified 2026-01-26; "boundaries created by the source 2010-01-01"; aligned to "BBS updates as of March 2025".
- **No union polygons in v03.** Union (ADM4) codes come from the `bgd_adminpoints` layer (valid_on 2020-11-13).
- **Two code schemes:**
  - `HDX_PCODE` (v03), e.g. `BD50810010`: `BD` + the DGHS/BBS geocode.
  - `HDX_PCODE_2020` (2020 points), e.g. `BD508110`, `BD50811021`.

## Counts

| District | Upazilas | Unions | Paurashavas |
|---|---|---|---|
| Bogura | 12 | 109 | 12 |
| Chapainawabganj | 5 | 45 | 4 |
| Joypurhat | 5 | 32 | 4 |
| Naogaon | 11 | 99 | 3 |
| Natore | 7 | 52 | 8 |
| Pabna | 9 | 74 | 9 |
| Rajshahi | 9 (+ RCC: 4 thanas, 30 wards) | 71 | 14 |
| Sirajganj | 9 | 82 | 6 |
| **Division** | **67 (+1 city corporation)** | **564** | **60** |

HDX upazila areas (km²), Rajshahi District: Bagha 185.7 · Bagmara 366.2 · Charghat 174.4 · Durgapur 199.5 · Godagari 490.0 · Mohanpur 161.9 · Paba 305.3 · Puthia 196.1 · Tanore 297.2 · RCC 46.5 · district 2,422.6.

## Union counts vs seed and master

| District | HDX 2020 | Seed | Master | Difference |
|---|---|---|---|---|
| Rajshahi | 71 | 71 | 71 | identical per upazila (6/16/6/7/9/6/8/6/7); does not support the local "Bagha 7 / 72" claim |
| Bogura | 109 | 108 | 108 | extra `Sultanganj (Part)` in Shajahanpur; master Gabtali 12 / Sonatala 6 vs 11 / 7 |
| Pabna | 74 | 73 | 73 | extra `Munotosh` in Bhangura (74 = BBS 2022 count) |
| Sirajganj | 82 | 82 | 83 | master Ullapara 14 |
| Natore | 52 | 52 | 52 | 2020 points have no Naldanga: its 5 unions sit under Natore Sadar |
| Chapainawabganj / Joypurhat / Naogaon | 45 / 32 / 99 | same | same | — |

## Crosswalk (`crosswalk.csv`)

- Districts 8/8, upazilas 67/67.
- Unions 551/564 (97.7%): 411 high, 129 medium, 11 low confidence; 13 unmatched, with candidates in `notes`.
- Rajshahi District unions 71/71 (44 high, 25 medium, 2 low: Salua↔Solua, Char Ashariadaha↔Asariadaha); paurashavas 14/14.
- Bogura City Corporation is not in HDX.

## Cautions

- No Bangla names in the source.
- The Rishikul (Godagari) and RCC Ward No-14 label points fall inside the v03 Paba polygon.
- HDX calls ADM4 "not officially confirmed": keep `verified=false`.
