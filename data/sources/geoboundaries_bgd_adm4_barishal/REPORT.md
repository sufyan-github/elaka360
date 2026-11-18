# geoBoundaries BGD ADM4 — Barishal Division

- **Source:** geoBoundaries gbOpen BGD-ADM4-29066614, year represented 2020, built 2023-12-12, derived from the HDX "administrative-boundaries-of-bangladesh-as-of-2015" dataset. Same national file as the earlier runs.
- **Run:** `python3 -I data/sources/geoboundaries_bgd_adm4/fetch.py --division barishal --cache <scratch>`, after the HDX Barishal run (accessed 2026-11-18). Key `GEOBOUNDARIES_BGD_ADM4_BARISHAL`, division `barishal`, kind `geoboundaries_adm4`. No change to fetch.py was needed.
- **Rerun check:** Rajshahi (no `--division`), Rangpur, Dhaka, Chattogram and Khulna into a scratch folder: areas.csv, boundaries.geojson and facts.csv byte-identical.
- **Licence:** CC BY 3.0 IGO. Attribution: geoBoundaries (Runfola et al. 2020); BBS; OCHA ROAP.
- **Coverage:** 401 polygons: 348 unions, 23 paurashavas, 30 city wards.

| District (as printed) | Unions | Paurashavas | Wards |
|---|---:|---:|---:|
| Barisal | 85 | 5 | 30 |
| Patuakhali | 70 | 4 | |
| Bhola | 68 | 5 | |
| Pirojpur | 51 | 3 | |
| Barguna | 42 | 4 | |
| Jhalokati | 32 | 2 | |

- **Codes:** HDX 2020 P-codes are attached by point-in-polygon from `../hdx_cod_ab_bgd_barishal/raw/bgd_adminpoints_barishal.geojson`. All 401 label points matched one-to-one; no problems.
- **No non-union units** among the "union" polygons (no forest ranges, cantonments).
- **Seed ids:** through `../hdx_cod_ab_bgd_barishal/crosswalk.csv`.
  - 322 union polygons map to a seed union at high or medium confidence (the importer uses only those); 13 more have a low-confidence match that is not used, and 13 have none.
  - Paurashava polygons have no seed id (the seed has no Barishal Division pourashavas yet); ward polygons have none either (no seed ward level).
  - See the HDX report for the doubtful Chhota Bagi ↔ Amtali Chotobogi pair.
- **Barishal City Corporation:**
  - The 30 ward polygons (Ward No-01 … 30, none split) lie inside the HDX v03 city-corporation polygon. Their total computed area is 55.76 km², vs HDX v03 58.5 km².
  - In `areas.csv` they hang under "Barisal Sadar (Kotwali)" as printed in the 2020 points.
  - The numbering 1–30 matches the 30 city wards of BBS 2022.
- **Coordinates:** lat/lon is the area-weighted centroid. 18 centroids fall outside their own polygon and are flagged in `notes`: Barguna, Durga Pasha, Hizla Gaurabdi, Ward No-04, Ward No-06, Mehendiganj, Char Manika, Jinnaghar, Nilkamal, Medua, Dakshin Joynagar, Manpura, Chanchra, Sonapur, Mollahat, Rangopaldi, Chakamaiya, Matibhanga.
- **Area:** `area_km2` is computed by Elaka360 and is not official.
- **Vintage:** ~2015–2020. Unions created later are not reflected (BBS 2022: 362 unions vs 348 here), e.g. four more in Borhanuddin and the Ulania split in Mehendiganj. Taltali/Rangabali unions are filed under Amtali/Galachipa as in the 2020 points. No Bangla names.
- **Size:** `boundaries.geojson` is 0.97 MB (Douglas-Peucker 0.0002°, 5 decimals, as before).
- **Not committed:** the ~340 MB national file; `fetch.py` rebuilds from it.
