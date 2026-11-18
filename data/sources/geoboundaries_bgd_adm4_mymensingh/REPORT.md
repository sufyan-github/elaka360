# geoBoundaries BGD ADM4 — Mymensingh Division

- **Source:** geoBoundaries gbOpen BGD-ADM4-29066614, year represented 2020, built 2023-12-12, derived from the HDX "administrative-boundaries-of-bangladesh-as-of-2015" dataset. Same national file as the earlier runs.
- **Run:** `python3 -I data/sources/geoboundaries_bgd_adm4/fetch.py --division mymensingh --cache <scratch>`, after the HDX Mymensingh run (accessed 2026-11-18). Key `GEOBOUNDARIES_BGD_ADM4_MYMENSINGH`, division `mymensingh`, kind `geoboundaries_adm4`.
- **fetch.py change:** none.
- **Rerun check:** Rajshahi (no `--division`) into a scratch folder: areas.csv, boundaries.geojson and facts.csv byte-identical. SOURCE.json differs only in `accessed`.
- **Licence:** CC BY 3.0 IGO. Attribution: geoBoundaries (Runfola et al. 2020); BBS; OCHA ROAP.
- **Coverage:** 378 polygons: 352 unions, 26 paurashavas, no wards.

| District (as printed) | Unions | Paurashavas |
|---|---:|---:|
| Mymensingh | 146 | 10 |
| Netrakona | 86 | 6 |
| Jamalpur | 68 | 6 |
| Sherpur | 52 | 4 |

- **Codes:** HDX 2020 P-codes are attached by point-in-polygon from `../hdx_cod_ab_bgd_mymensingh/raw/bgd_adminpoints_mymensingh.geojson`. All 378 label points matched one-to-one; no problems.
- **No non-union units** among the "union" polygons (no cantonment or forest unit). Char unions are ordinary unions.
- **Seed ids:** through `../hdx_cod_ab_bgd_mymensingh/crosswalk.csv`.
  - 333 union polygons map to a seed union at high or medium confidence (the importer uses only those).
  - 5 more have a low-confidence match that is not used, and 14 have none (spelling variants listed in the HDX report).
  - Paurashava polygons have no seed id: the seed has no Mymensingh Division pourashavas yet.
- **Units filed under 2020 parents:** the 10 Tarakanda unions hang under "Phulpur", as in the 2020 points.
- **Mymensingh City Corporation:**
  - No ward polygons. The national file has no ward polygon in the city area; the city is covered by a "Mymensingh Paurashava" polygon (`BD45615299`), which is kept at level `pourashava` as printed.
  - BBS 2022 has 33 city wards and no Mymensingh Paurashava, so this polygon is the old paurashava extent, not the city corporation.
- **Coordinates:** lat/lon is the area-weighted centroid. 5 centroids fall outside their own polygon and are flagged in `notes`: Melandaha Paurashava, Ghoshgaon, Saltia, Amirabari, Loneshwar.
- **Area:** `area_km2` is computed by Elaka360 and is not official.
- **Vintage:** ~2015–2020. Unions created later are not reflected (BBS 2022: 351 unions, 27 paurashavas). Missing paurashavas: Bakshiganj, Haluaghat, Hazrabari. No Bangla names.
- **Size:** `boundaries.geojson` is 1.17 MB (Douglas-Peucker 0.0002°, 5 decimals, as before).
- **Not committed:** the ~340 MB national file; `fetch.py` rebuilds from it.
