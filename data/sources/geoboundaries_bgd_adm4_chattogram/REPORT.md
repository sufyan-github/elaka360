# geoBoundaries BGD ADM4 — Chattogram Division

- **Source:** geoBoundaries gbOpen BGD-ADM4-29066614, year represented 2020, built 2023-12-12, derived from the HDX "administrative-boundaries-of-bangladesh-as-of-2015" dataset (now 404). Same national file as the Rajshahi/Rangpur/Dhaka runs.
- **Run:** `python3 -I data/sources/geoboundaries_bgd_adm4/fetch.py --division chattogram --cache <scratch>`, after the HDX Chattogram run (accessed 2026-11-17). Key `GEOBOUNDARIES_BGD_ADM4_CHATTOGRAM`, division `chattogram`, kind `geoboundaries_adm4`. No change to fetch.py was needed.
  - A first attempt earlier the same day failed: the geoBoundaries API timed out (HTTPS and HTTP) between 18:40 and 18:56 (+06). The run above was made after the API answered again; nothing was worked around.
- **Licence:** CC BY 3.0 IGO. Attribution: geoBoundaries (Runfola et al. 2020); BBS; OCHA ROAP.
- **Coverage:** 1,063 polygons: 953 unions, 59 paurashavas, 51 city wards (Chattogram City Corporation, under its metro thanas).

| District (as printed) | Unions | Paurashavas | Wards |
|---|---:|---:|---:|
| Chittagong | 197 | 10 | 51 |
| Comilla | 188 | 10 | |
| Brahamanbaria | 100 | 4 | |
| Noakhali | 91 | 8 | |
| Chandpur | 88 | 7 | |
| Cox's Bazar | 71 | 4 | |
| Lakshmipur | 58 | 4 | |
| Rangamati | 49 | 2 | |
| Feni | 43 | 5 | |
| Khagrachhari | 38 | 3 | |
| Bandarban | 30 | 2 | |

- **Codes:** HDX 2020 P-codes are attached by point-in-polygon from `../hdx_cod_ab_bgd_chattogram/raw/bgd_adminpoints_chattogram.geojson`. All 1,063 label points matched one-to-one; no problems.
- **Seed ids:** through `../hdx_cod_ab_bgd_chattogram/crosswalk.csv`. 838 union polygons map to a seed union at high or medium confidence (the importer uses only those); 45 more have a low-confidence match that is not used. Paurashava polygons have no seed id (the seed has no Chattogram pourashavas before the BBS merge); ward polygons have none either (no seed ward level before the merge).
- **City corporations:**
  - Chattogram: the 51 ward polygons (41 ward numbers, 10 split between two thanas as "(Part)") lie inside the city corporation. Their numbering 1–41 matches the 41 city wards of BBS 2022.
  - Cumilla: no ward polygons. The area is still covered by the former Comilla and Comilla Dakshin Paurashava polygons (the city corporation replaced them in 2011).
- **Coordinates:** lat/lon is the area-weighted centroid. 33 centroids fall outside their own polygon (thin or multi-part shapes, e.g. chars and islands); the collector counted them but did not flag them in `notes`.
- **Area:** `area_km2` is computed by Elaka360 and is not official.
- **Vintage:** ~2015–2020. Newer upazilas (Karnaphuli, Eidgaon, Lalmai, Guimara) and the unions moved into them are not reflected; their unions are filed under the old upazilas. No Bangla names.
- **Size:** `boundaries.geojson` is 2.7 MB (Douglas-Peucker 0.0002°, 5 decimals, as before).
- **Not committed:** the ~340 MB national file; `fetch.py` rebuilds from it.
