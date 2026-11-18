# geoBoundaries BGD ADM4 — Khulna Division

- **Source:** geoBoundaries gbOpen BGD-ADM4-29066614, year represented 2020, built 2023-12-12, derived from the HDX "administrative-boundaries-of-bangladesh-as-of-2015" dataset (now 404). Same national file as the earlier runs.
- **Run:** `python3 -I data/sources/geoboundaries_bgd_adm4/fetch.py --division khulna --cache <scratch>`, after the HDX Khulna run (accessed 2026-11-18). Key `GEOBOUNDARIES_BGD_ADM4_KHULNA`, division `khulna`, kind `geoboundaries_adm4`. No change to fetch.py was needed.
- **Rerun check:** Rajshahi/Rangpur/Dhaka/Chattogram into a scratch folder: areas.csv, boundaries.geojson and facts.csv byte-identical.
- **Licence:** CC BY 3.0 IGO. Attribution: geoBoundaries (Runfola et al. 2020); BBS; OCHA ROAP.
- **Coverage:** 642 polygons: 574 unions, 36 paurashavas, 32 city wards (Khulna City Corporation, under its metro thanas).

| District (as printed) | Unions | Paurashavas | Wards |
|---|---:|---:|---:|
| Jessore | 91 | 8 | |
| Satkhira | 79 | 2 | |
| Bagerhat | 77 | 3 | |
| Khulna | 70 | 2 | 32 |
| Jhenaidah | 67 | 6 | |
| Kushtia | 66 | 5 | |
| Narail | 38 | 3 | |
| Magura | 36 | 1 | |
| Chuadanga | 32 | 4 | |
| Meherpur | 18 | 2 | |

- **Codes:** HDX 2020 P-codes are attached by point-in-polygon from `../hdx_cod_ab_bgd_khulna/raw/bgd_adminpoints_khulna.geojson`. All 642 label points matched one-to-one; no problems.
- **Not union parishads:** 5 of the "union" polygons are Sundarbans forest ranges: Chandpai Range, Sharankhola Range, Khulna Range, Nalian Range, Satkhira Range. They have no seed id.
- **Seed ids:** through `../hdx_cod_ab_bgd_khulna/crosswalk.csv`.
  - 538 union polygons map to a seed union at high or medium confidence (the importer uses only those); 18 more have a low-confidence match that is not used, and 18 have none.
  - Paurashava polygons have no seed id (the seed has no Khulna Division pourashavas yet); ward polygons have none either (no seed ward level).
- **Khulna City Corporation:**
  - The 32 ward polygons lie inside the city corporation: 31 ward numbers, Ward No-02 split between Daulatpur and Khan Jahan Ali as "(part)". The numbering 1–31 matches the 31 city wards of BBS 2022.
  - The polygons of Aranghata (filed under Daulatpur thana), Atra Gilatala and Jugipole (Khan Jahan Ali) are unions that BBS 2022 and the seed place in Dighalia and Phultala; they have no seed id here.
- **Coordinates:** lat/lon is the area-weighted centroid. 12 centroids fall outside their own polygon and are flagged in `notes`: Maghia, Sharankhola Range, Manirampur, Benapole, Paglakanai, Ward No-24, Ward No-25, Manohardia, Malihad, Pahardanga, Chandibarpur, Jalalpur.
- **Area:** `area_km2` is computed by Elaka360 and is not official.
- **Vintage:** ~2015–2020. Unions created later (e.g. BBS 2022 has 41 unions in Chuadanga vs 32 here, 20 in Meherpur vs 18) are not reflected. No Bangla names.
- **Size:** `boundaries.geojson` is 2.1 MB (Douglas-Peucker 0.0002°, 5 decimals, as before).
- **Not committed:** the ~340 MB national file; `fetch.py` rebuilds from it.
