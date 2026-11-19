# HDX COD-AB Bangladesh v03 — Rangpur Division

- **Source:** https://data.humdata.org/dataset/cod-ab-bgd. Original source BBS; contributed by OCHA ROAP; published by OCHA FIS / HDX.
- **Licence:** CC BY-IGO 3.0.
- **Version:** v03, valid_on 2023-05-21, reviewed 2025-06-01, resource modified 2026-01-26 (same national file as the Rajshahi run).
- **Run:** `python3 -I data/sources/hdx_cod_ab_bgd/fetch.py --division rangpur` (accessed 2026-11-17). Key `HDX_COD_AB_BGD_RANGPUR`, division `rangpur`, kind `hdx_cod_ab`.
- **No union polygons in v03.** Union (ADM4) codes come from the `bgd_adminpoints` layer (valid_on 2020-11-13). Polygons for them are in `../geoboundaries_bgd_adm4_rangpur`.
- **Two code schemes:** `HDX_PCODE` (v03, e.g. `BD55850049` Rangpur Sadar) and `HDX_PCODE_2020` (2020 points, e.g. `BD558549`, `BD55854994`).

## Counts

| District | Upazilas (v03) | Unions (2020 points) | Paurashavas (2020 points) | Seed unions |
|---|---|---|---|---|
| Dinajpur | 13 | 101 | 8 | 102 |
| Gaibandha | 7 | 82 | 3 | 82 |
| Kurigram | 9 | 72 | 3 | 72 |
| Lalmonirhat | 5 | 45 | 2 | 45 |
| Nilphamari | 6 | 60 | 4 | 60 |
| Panchagarh | 5 | 43 | 2 | 43 |
| Rangpur | 8 (+ Rangpur City Corporation) | 83 | 3 | 83 |
| Thakurgaon | 5 | 51 | 3 | 53 |
| **Division** | **58 (+1 city corporation)** | **537** | **28** | **540** |

`boundaries.geojson` (1.2 MB) has 68 polygons: 1 division, 8 districts, 58 upazilas and the city corporation (`BD55857500`).
`facts.csv` has 68 `area_km2` values (HDX `area_sqkm`, not official BBS areas); the division is 16,282.75 km².

## Crosswalk (`crosswalk.csv`) to `data/seed/geo/admin_areas.csv`

Built with the same matcher as Rajshahi: name tiers within the same parent (exact → banglish → skeleton → fuzzy ≥ 0.8),
then a second pass within the same district. Matches are never forced. Districts use a hand-checked P-code table
(`DISTRICT_SEED_BY_DIV`).

- Districts 8/8 (20053–20060) and Rangpur City Corporation → 50008.
- Upazilas 58/58: 49 high and 9 medium confidence. The medium ones are Kaharole↔Kaharol, Nababganj↔Nawabganj,
  Rajibpur↔Charrajibpur, Kishoreganj↔Kishorganj, Saidpur↔Syedpur, Tentulia↔Tetulia, Badarganj↔Badargonj,
  Pirganj↔Pirgonj and Taraganj↔Taragonj.
- Unions 521/537 (97.0 %): 341 high, 160 medium, 20 low. 16 HDX unions are unmatched, and 19 seed unions have no HDX
  unit (`no_source_unit`).
- Paurashavas 0/28: the seed has no pourashava rows in Rangpur Division yet (`no_seed_unit`).

Some unmatched pairs look like the same union but fall below the matcher's threshold. They are left unmatched (not
applied); check them before use:
- Deor↔Dior (Birampur)
- Mogalbachha↔Mogolbasa (Kurigram Sadar)
- Dantbhanga↔Dadevanga (Rowmari)
- Akcha↔Ahcha (Thakurgaon Sadar)
- Kolkanda↔Kolcondo (Gangachara)
- Dahabanda↔Dohbond (Sundarganj)
- Chhaola↔Saula (Pirgachha)
- Chaitrakul↔Chattracol (Pirganj)
- Hazradanga↔Chengthi Hazra Danga (Debiganj)
- Benghari Banagram↔Banghari (Boda)
- Bhojanpur Debnagar↔Debnagar (Tetulia)
- Kaunia Bala Para↔Balapara and Kursha↔Kurshaupk (Kaunia)
- Kursha↔Kurshatara (Taraganj)
- Unclear: Khurda Kamarpur (Sadullapur; seed Khodkomor?) and Badarganj union (Badarganj; seed Kalupara?).

Seed unions with no counterpart in the 2020 points (probably newer unions): Rajarampur (Birol), Ruhia Pashchim and
Dholarhat (Thakurgaon Sadar).

Low-confidence matches to review (`confidence=low`) include Chhatail↔Shatail, Fatehjanapur↔Fatejangpur,
Kazihal↔Kagihal, Chehelgazi↔Chealgazi, Bhangamon↔Bhangamor, Thetroy↔Thetrai, Mirzapur↔Mirgapur, Taria↔Toria,
Tirnaihat↔Timaihat, Ramnathpur↔Ramnathpurupb, Pashuram↔Porshuram, Latifpur↔Latibpur and Sayar↔Soyar. One skeleton
match, Kumar Para↔Kamarpara (Saghata), also needs checking.

## Cautions

- No Bangla names in the source.
- 26 of the 28 paurashava points are named only "Paurashava"; Setabganj and Sundarganj carry a town name. Their
  upazila is in `parent_name_en`.
- `BD55854999` "Paurashava" under Rangpur Sadar is the old Rangpur Paurashava, which became Rangpur City Corporation
  in 2012.
- The 2020 layer has no thana or ward points for Rangpur City Corporation.
- 9 label points lie outside their v03 upazila polygon:
  - 8 Rangpur Sadar points (Darshana, Pashuram, Paurashava, Rajendrapur, Satgara, Tamphat, Tapodhan, Uttam) fall
    inside the City Corporation polygon. These union records are probably outdated.
  - Khaleya (Gangachara) falls inside the Rangpur Sadar polygon.
- HDX calls ADM4 "not officially confirmed": keep `verified=false`.
