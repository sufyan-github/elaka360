# geoBoundaries BGD ADM4 — Dhaka Division

- **Source:** geoBoundaries gbOpen BGD-ADM4-29066614, year represented 2020, built 2023-12-12, derived from the HDX "administrative-boundaries-of-bangladesh-as-of-2015" dataset (now 404). Same national file as the Rajshahi/Rangpur runs.
- **Run:** `python3 -I data/sources/geoboundaries_bgd_adm4/fetch.py --division dhaka`, after the HDX Dhaka run (accessed 2026-11-17). Key `GEOBOUNDARIES_BGD_ADM4_DHAKA`, division `dhaka`, kind `geoboundaries_adm4`. No change to fetch.py was needed.
- **Licence:** CC BY 3.0 IGO. Attribution: geoBoundaries (Runfola et al. 2020); BBS; OCHA ROAP.
- **Coverage:** 1,078 polygons: 904 unions, 59 paurashavas, 115 city wards (old Dhaka City Corporation wards, under metro thanas).

| District | Unions | Paurashavas | Wards |
|---|---:|---:|---:|
| Dhaka | 85 (23 of them under metro thanas) | 3 | 115 |
| Faridpur | 79 | 4 | |
| Gazipur | 44 | 4 | |
| Gopalganj | 68 | 4 | |
| Kishoreganj | 110 | 8 | |
| Madaripur | 59 | 3 | |
| Manikganj | 65 | 2 | |
| Munshiganj | 67 | 2 | |
| Narayanganj | 41 | 6 | |
| Narsingdi | 70 | 6 | |
| Rajbari | 42 | 3 | |
| Shariatpur | 65 | 5 | |
| Tangail | 109 | 9 | |

- **Codes:** HDX 2020 P-codes are attached by point-in-polygon from `../hdx_cod_ab_bgd_dhaka/raw/bgd_adminpoints_dhaka.geojson`. All 1,078 label points matched one-to-one with identical names; no problems.
- **Seed ids:** through `../hdx_cod_ab_bgd_dhaka/crosswalk.csv`, 850 of the 904 union polygons map to a seed union (646 high, 183 medium, 21 low confidence). 54 union polygons (23 former unions under DNCC/DSCC metro thanas, 31 elsewhere), all 59 paurashava polygons (the seed has no Dhaka pourashavas) and all 115 ward polygons (no seed ward level) have no seed id.
- **City corporations:** the ward polygons are not linked to a city corporation in the source. By their HDX label points, 49 lie in Dhaka North and 66 in Dhaka South. Their numbers are the old undivided Dhaka City Corporation numbering (1–92, 98), not current DNCC/DSCC ward numbers. There are no ward polygons for Gazipur or Narayanganj City Corporation; that area is still covered by the pre-city-corporation unions and paurashavas (Gazipur, Tongi, Narayanganj, Siddirganj, Kadam Rasul paurashavas; Basan, Gachha, Kashimpur, Kayaltia, Konabari, Pubail unions).
- **(Part) units:** 52 polygons are named "(part)" (unions or wards split between thanas/upazilas).
- **Coordinates:** lat/lon is the area-weighted centroid. 22 centroids fall outside their polygon and are flagged in `notes`: Ward No-46, Ward No-10, Ward No-92, Ward No-83, Char Jhaukanda, Kamarkhali, Maharajpur, Bangal Para, Gurai, Nabagram, Madaripur Paurashava, Singair, Shambhupura, Dhamgar, Chinishpur, Mirzapur, Sadhar Char, Chhota Bhakla, Dhakhin Tarabunia, Dhanbari, Paiska, Bhadra.
- **Area:** `area_km2` is computed by Elaka360 and is not official. The sum is 20,475.6 km², vs 20,426.5 km² for the HDX v03 division.
- **Vintage:** ~2015–2020. Units absorbed into the Dhaka North/South (2016), Gazipur (2013) and Narayanganj (2011) city corporations still appear as unions/paurashavas; Dasar upazila (from Kalkini) is not reflected. No Bangla names.
- **Size:** `boundaries.geojson` is 2.6 MB (Douglas-Peucker 0.0002°, 5 decimals, as for Rajshahi/Rangpur).
- **Not committed:** the ~340 MB national file; `fetch.py` rebuilds from it.
