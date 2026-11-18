# HDX COD-AB Bangladesh v03 — Dhaka Division

- **Source:** https://data.humdata.org/dataset/cod-ab-bgd. Original source BBS; contributed by OCHA ROAP; published by OCHA FIS / HDX.
- **Licence:** CC BY-IGO 3.0.
- **Version:** v03, valid_on 2023-05-21, reviewed 2025-06-01, resource modified 2026-01-26 (same national file as the Rajshahi/Rangpur runs).
- **Run:** `python3 -I data/sources/hdx_cod_ab_bgd/fetch.py --division dhaka` (accessed 2026-11-17). Key `HDX_COD_AB_BGD_DHAKA`, division `dhaka`, kind `hdx_cod_ab`.
- **No union polygons in v03.** Union (ADM4) codes come from the `bgd_adminpoints` layer (valid_on 2020-11-13); polygons for them are in `../geoboundaries_bgd_adm4_dhaka`.
- **Two code schemes:** `HDX_PCODE` (v03, e.g. `BD30262500` Dhaka North City Corporation) and `HDX_PCODE_2020` (2020 points, e.g. `BD302604` Badda thana, `BD30260413` Badda union).

## Counts

| District | Upazilas (v03) | City corporations (v03) | Unions (2020 points) | Paurashavas (2020 points) | Seed unions |
|---|---:|---|---:|---:|---:|
| Dhaka | 5 | Dhaka North, Dhaka South | 85 (62 in the 5 upazilas + 23 under metro thanas) | 3 | 62 |
| Faridpur | 9 | | 79 | 4 | 79 |
| Gazipur | 5 | Gazipur | 44 | 4 | 43 |
| Gopalganj | 5 | | 68 | 4 | 67 |
| Kishoreganj | 13 | | 110 | 8 | 109 |
| Madaripur | 5 | | 59 | 3 | 59 |
| Manikganj | 7 | | 65 | 2 | 65 |
| Munshiganj | 6 | | 67 | 2 | 67 |
| Narayanganj | 5 | Narayanganj | 41 | 6 | 38 |
| Narsingdi | 6 | | 70 | 6 | 70 |
| Rajbari | 5 | | 42 | 3 | 43 |
| Shariatpur | 6 | | 65 | 5 | 64 |
| Tangail | 12 | | 109 | 9 | 110 |
| **Division** | **89** | **4** | **904** | **59** | **876** |

The 2020 points also have 41 metro thanas of Dhaka district (`BD3026xx`, level `thana`) and 115 ward points under those
thanas. There are no thana or ward points for Gazipur or Narayanganj City Corporation.

`boundaries.geojson` (1.1 MB) has 107 polygons: 1 division, 13 districts, 89 upazilas and 4 city corporations (Dhaka
South `BD30262000`, Dhaka North `BD30262500`, Gazipur `BD30333300`, Narayanganj `BD30674400`). `facts.csv` has 107
`area_km2` values (HDX `area_sqkm`, not official BBS areas). Division 20,426.53 km²; Dhaka North 205.29, Dhaka South
98.94, Gazipur 319.66, Narayanganj 48.71.

## City corporations, metro thanas and wards

- In the source, the 2020 thana and ward points are not tied to a city corporation: parent = metro thana, whose parent
  is Dhaka district. `areas.csv` keeps them that way.
- By point-in-polygon against the v03 city-corporation polygons (checked for this report, not written to `areas.csv`):
  49 ward points fall in Dhaka North (37 ward numbers: 01–23, 37–47, 54, 55, 98) and 66 in Dhaka South (56 numbers:
  24–36, 48–53, 56–92). All 23 union points under metro thanas fall in Dhaka North or Dhaka South.
- The ward names (`Ward No-01` … `Ward No-92`, `Ward No-98 (Rest. Area)`) use the numbering of the old, undivided Dhaka
  City Corporation. The 2011 split and the 2016 extension renumbered the wards, so these numbers do **not** match current
  DNCC/DSCC wards (BBS 2022: DSCC 1–75, DNCC 1–54). Do not join them by number.
- The 23 "unions" under metro thanas (Badda, Beraid, Bhatara, Satarkul, Dakshinkhan, Dumni, Uttar Khan, Harirampur
  (Part), Demra, Matuail, Saralia, Dhania, Shyampur, Sultanganj, Dakshingaon, Nasirabad, Manda; several split as
  "(part)") are the unions the 2016 extension absorbed into DNCC/DSCC. They are kept as level `union`, as printed, and
  are unmatched in the crosswalk (the seed has no thana level).
- Gazipur City Corporation (2013) and Narayanganj City Corporation (2011) are not reflected in the 2020 points:
  - Gazipur: Gazipur and Tongi paurashavas and the unions Basan, Gachha, Kashimpur, Kayaltia, Konabari and Pubail
    (under Gazipur Sadar). All 8 label points lie inside the v03 Gazipur City Corporation polygon.
  - Narayanganj: Narayanganj, Siddirganj and Kadam Rasul paurashavas lie inside the v03 Narayanganj City Corporation
    polygon.

## Crosswalk (`crosswalk.csv`) to `data/seed/geo/admin_areas.csv`

Same matcher as Rajshahi/Rangpur: name tiers within the same parent (exact → banglish → skeleton → fuzzy ≥ 0.8), then a
second pass within the same district. Matches are never forced. Districts use a hand-checked P-code table
(`DISTRICT_SEED_BY_DIV["dhaka"]`, added for this run); all 13 names are identical.

- Districts 13/13 (20040–20052). City corporations 4/4: Dhaka North → 50001, Dhaka South → 50002, Gazipur → 50011, Narayanganj → 50010.
- Upazilas 89/89: 81 high, 7 medium (Karimganj↔Karimgonj, Mithamain↔Mithamoin, Daulatpur↔Doulatpur, Shibalay↔Shibaloy, Singair↔Singiar, Manohardi↔Monohardi, Bhuanpur↔Bhuapur), 1 low (Louhajang↔Louhajanj).
- Unions 850/904 (94.0 %): 646 high, 183 medium, 21 low. 54 HDX unions are unmatched (23 under metro thanas, 31 elsewhere); 26 seed unions have no HDX unit (`no_source_unit`).
- Paurashavas 0/59: the seed has no pourashava rows in Dhaka Division (`no_seed_unit`).
- Thanas (41) and wards (115): `no_seed_level`.

Probable pairs below the threshold, left unmatched (check before use): Elongjuri↔Alonjori (Itna), Dhala↔Dhola (Tarail),
Banagram↔Bongaon (Savar), Bayratala Dakshin↔Bahertala South and Bayratala Uttar↔Baheratala North (Shibchar),
Lesraganj↔Lacharagonj (Harirampur), Joy Mantap↔Joymonto (Singair), Arial↔Arial Baligaon (Tongibari),
Kalagachhia↔Kolagathia (Bandar), Bekra↔Bekrah Atgram (Nagarpur), Danya↔Dyenna (Tangail Sadar); Bhedarganj: Char
Census↔Charsensas, Dhakhin Tarabunia↔South Tarabunia, Tarabunia↔North Tarabunia (?), Digar Mahishkhali↔D.M Khali;
Fateh Jangapur↔Fategongpur (Naria), Mohammadpur↔Mahmudpur (Shariatpur Sadar), Bara Krishnagar↔Bknagar (Zanjira).
Unclear: Gariber Char (Gosairhat; seed Alaolpur?), Birhati (Bhuapur; seed Aloa?), Dhanbari (seed Jadunathpur?), Chamta
(Naria), Katiadi, Araihazar, Kaliganj (code space of Gazipur Sadar), Suagram (Kotalipara), Sadasardi (Araihazar),
Fatullah (part) (Narayanganj Sadar), Mirzapur and Radhanagar (Palash), Elenga (Kalihati; now a paurashava).

Seed unions with no counterpart in the 2020 points (newer unions or the spellings above): Diara (Belabo), Krisnopur
(Monohardi), Dariapur and Kalmegha (Sakhipur), Kalukhali (Kalukhali), plus the seed names listed above.

Low-confidence matches to review (`confidence=low`): Manikdaha↔Manikdha, Dhaljora↔Dhaliora, Jamalpur↔Jamalpurnew,
Singasree↔Sinhasree, Toke↔Tokh, Ghagar↔Ghaghor, Raituti↔Raytoti, Masua↔Mosua, Gurai↔Guroi, Talganga↔Taljanga,
Kayaria↔Koyaria, Boyra↔Baira (Harirampur), Boyra↔Buyra (Singair), Silai↔Shiloy, Chitrakot↔Chitracoat, Kayain↔Keyain,
Haizadi↔Highjadi, Jangal↔Janjal, Chhaygaon↔Saygaon, Deoli↔Deuli, Jadabpur↔Jaduppur.

## Cautions

- No Bangla names in the source. All 59 paurashava points carry a town name.
- Label points outside their own v03 upazila polygon (besides the city-corporation cases above):
  - 5 Kalkini unions (Baligram, Dasar, Gopalpur, Kazibakai, Nabagram) lie in the v03 Dasar upazila (split from Kalkini;
    no 2020 point). The seed also keeps them under Kalkini.
  - Chandpur (Boalmari) lies in Faridpur Sadar; Dana Patali (Kishoreganj Sadar) in Katiadi.
  - Dhakhin Tarabunia (Bhedarganj) and Saorail (Kalukhali) lie in no upazila polygon.
- HDX calls ADM4 "not officially confirmed": keep `verified=false`.
