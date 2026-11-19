# geoBoundaries BGD ADM4 — Rangpur Division

- **Source:** geoBoundaries gbOpen BGD-ADM4-29066614, year represented 2020, built 2023-12-12. It is derived from the HDX "administrative-boundaries-of-bangladesh-as-of-2015" dataset (now 404). Same national file as the Rajshahi run.
- **Run:** `python3 -I data/sources/geoboundaries_bgd_adm4/fetch.py --division rangpur`, after the HDX Rangpur run (accessed 2026-11-17). Key `GEOBOUNDARIES_BGD_ADM4_RANGPUR`, division `rangpur`, kind `geoboundaries_adm4`.
- **Licence:** CC BY 3.0 IGO. Attribution: geoBoundaries (Runfola et al. 2020); BBS; OCHA ROAP.
- **Coverage:** 565 polygons: 537 unions and 28 paurashavas. There are no city wards, because the HDX 2020 point layer has none for Rangpur City Corporation.

| District | Unions | Paurashavas |
|---|---|---|
| Dinajpur | 101 | 8 |
| Gaibandha | 82 | 3 |
| Kurigram | 72 | 3 |
| Lalmonirhat | 45 | 2 |
| Nilphamari | 60 | 4 |
| Panchagarh | 43 | 2 |
| Rangpur | 83 | 3 |
| Thakurgaon | 51 | 3 |

- **Codes:** HDX 2020 P-codes are attached by point-in-polygon from `../hdx_cod_ab_bgd_rangpur/raw/bgd_adminpoints_rangpur.geojson`. All 565 label points matched one-to-one with identical names; no problems.
- **Seed ids:** through `../hdx_cod_ab_bgd_rangpur/crosswalk.csv`, 521 of the 537 union polygons map to a seed union (341 high, 160 medium, 20 low confidence). 16 union polygons and all 28 paurashava polygons have no seed id; the seed has no Rangpur pourashavas yet.
- **Coordinates:** lat/lon is the area-weighted centroid. 9 centroids fall outside their polygon and are flagged in `notes`: Mushidhat, Mogalbachha, Punchgachhi, Kachakata, Newashi, Baura, Kuchlibari, Daoabari, Pirganj.
- **Area:** `area_km2` is computed by Elaka360 and is not official. The sum is 16,355 km², vs 16,283 km² for the HDX v03 division.
- **Vintage:** ~2015–2020.
  - The Rangpur Sadar union polygons and the old Rangpur Paurashava polygon predate the City Corporation's current extent; several lie inside the v03 City Corporation polygon.
  - 26 paurashava polygons are named only "Paurashava".
  - No Bangla names.
- **Size:** `boundaries.geojson` is 2.3 MB (Douglas-Peucker 0.0002°, 5 decimals, as for Rajshahi).
- **Not committed:** the ~340 MB national file; `fetch.py` rebuilds from it.
