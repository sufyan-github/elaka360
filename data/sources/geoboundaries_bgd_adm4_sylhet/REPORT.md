# geoBoundaries BGD ADM4 — Sylhet Division

- **Source:** geoBoundaries gbOpen BGD-ADM4-29066614, year represented 2020, built 2023-12-12, derived from the HDX "administrative-boundaries-of-bangladesh-as-of-2015" dataset. Same national file as the earlier runs.
- **Run:** `python3 -I data/sources/geoboundaries_bgd_adm4/fetch.py --division sylhet --cache <scratch>`, after the HDX Sylhet run (accessed 2026-11-18). Key `GEOBOUNDARIES_BGD_ADM4_SYLHET`, division `sylhet`, kind `geoboundaries_adm4`.
- **fetch.py change:** polygon and label-point names are compared with runs of spaces ignored.
  - The polygon for BD60903221 is named "Dakshin  Sukhairrajapur" (two spaces); the HDX point has one. Before the change it was the only unassigned point.
  - `name_en` keeps the polygon name as printed.
- **Rerun check:** Rajshahi (no `--division`), Rangpur, Dhaka, Chattogram, Khulna and Barishal into a scratch folder:
  areas.csv, boundaries.geojson and facts.csv byte-identical. SOURCE.json differs only in `accessed`.
- **Licence:** CC BY 3.0 IGO. Attribution: geoBoundaries (Runfola et al. 2020); BBS; OCHA ROAP.
- **Coverage:** 379 polygons: 333 unions, 19 paurashavas, 27 city wards.

| District (as printed) | Unions | Paurashavas | Wards |
|---|---:|---:|---:|
| Sylhet | 102 | 4 | 27 |
| Sunamganj | 87 | 4 | |
| Habiganj | 77 | 6 | |
| Maulvibazar | 67 | 5 | |

- **Codes:** HDX 2020 P-codes are attached by point-in-polygon from `../hdx_cod_ab_bgd_sylhet/raw/bgd_adminpoints_sylhet.geojson`. All 379 label points matched one-to-one; no problems.
- **No non-union units** among the "union" polygons (no cantonment, tea estate or forest unit).
- **Seed ids:** through `../hdx_cod_ab_bgd_sylhet/crosswalk.csv`.
  - 295 union polygons map to a seed union at high or medium confidence (the importer uses only those).
  - 16 more have a low-confidence match that is not used, and 22 have none (see the HDX report).
  - Paurashava polygons have no seed id: the seed has no Sylhet Division pourashavas yet.
  - Ward polygons have none either: the seed has no ward level.
- **Units filed under 2020 parents:**
  - The 8 Shantiganj unions hang under "Dakshin Sunamganj".
  - Osmaninagar, Shayestaganj and Madhyanagar unions hang under Balaganj, Habiganj Sadar and Dharampasha, as in the 2020 points.
- **Sylhet City Corporation:**
  - The 27 ward polygons (Ward No-01 … 27, none split) lie inside the HDX v03 city-corporation polygon. Their total computed area is 26.80 km², vs HDX v03 27.05 km².
  - In `areas.csv` they hang under "Sylhet Sadar" as printed.
  - The numbering 1–27 matches the 27 city wards of BBS 2022.
- **Coordinates:** lat/lon is the area-weighted centroid. 11 centroids fall outside their own polygon and are flagged in `notes`: Satkapan, Gopaya, Tegharia, Murakari, Uttar Dakshinbhag, Sagarnal, Adampur, Ashidron, Atgaon, Dakshin Badal, Zakiganj.
- **Area:** `area_km2` is computed by Elaka360 and is not official.
- **Vintage:** ~2015–2020.
  - Unions created later are not reflected (BBS 2022: 341 unions vs 333 here), e.g. Bagha (Golapganj), Gowainghat Sadar, Maddho Jaflong and the Alirgaon split (Gowainghat), Jamalganj Uttar.
  - No Bangla names.
- **Size:** `boundaries.geojson` is 1.46 MB (Douglas-Peucker 0.0002°, 5 decimals, as before).
- **Not committed:** the ~340 MB national file; `fetch.py` rebuilds from it.
