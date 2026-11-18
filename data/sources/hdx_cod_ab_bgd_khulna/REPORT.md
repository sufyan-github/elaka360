# HDX COD-AB Bangladesh v03 — Khulna Division

- **Source:** https://data.humdata.org/dataset/cod-ab-bgd. Original source BBS; contributed by OCHA ROAP; published by OCHA FIS / HDX.
- **Licence:** CC BY-IGO 3.0.
- **Version:** v03, valid_on 2023-05-21, reviewed 2025-06-01, resource modified 2026-01-26 (same national file as the earlier runs).
- **Run:** `python3 -I data/sources/hdx_cod_ab_bgd/fetch.py --division khulna` (accessed 2026-11-18). Key `HDX_COD_AB_BGD_KHULNA`, division `khulna`, kind `hdx_cod_ab`.
- **No union polygons in v03.** Union (ADM4) codes come from the `bgd_adminpoints` layer (valid_on 2020-11-13). The matching union polygons come from geoBoundaries (`../geoboundaries_bgd_adm4_khulna`).
- **Two code schemes:** `HDX_PCODE` (v03, e.g. `BD40473300` Khulna City Corporation) and `HDX_PCODE_2020` (2020 points, e.g. `BD404751` Khulna Sadar thana, `BD40475131` Ward No-31).

## fetch.py changes for this run (all off for the earlier divisions)

- `DISTRICT_SEED_BY_DIV["khulna"]`: hand-checked district P-codes. All 10 names are identical to the seed.
- `UNIT_SEED_BY_DIV["khulna"]`: two upazilas checked against the seed's Bangla names (method `code_hand_checked`):
  - Dacope → Dakop (দাকোপ, 30213). No tier pairs them, and without the pin its 9 unions had no parent.
  - Paikgachha → Paikgasa (পাইকগাছা, 30206). The fuzzy tier pairs these correctly but only at `low`, which the importer does not use.
- `DIRECTION_WORD_DIVS` now includes `khulna`. Without it, the fuzzy tier paired Uttar Bedkashi (Koyra) with seed **South** Bedkashi, and Dakshin Bedkashi and Dakshin Khali stayed unmatched. With it, 4 unions match with a "direction word read as …" note: Uttar/Dakshin Bedkashi ↔ North/South Bedkashi, Dakshin Khali Union ↔ Southkhali, Dakshin Sreepur.
- Rajshahi/Rangpur/Dhaka/Chattogram reruns into a scratch folder:
  - areas, boundaries, facts and raw files: identical for all four; the Rangpur crosswalk is identical too.
  - Rajshahi, Dhaka and Chattogram `crosswalk.csv` differ only in pourashava rows. This is because the seed gained pourashavas after those folders were built: the HEAD version of fetch.py on the current seed gives the same output as the new one.

## Counts

| District (v03) | Upazilas (v03) | City corporations (v03) | Unions (2020 points) | Paurashavas (2020 points) | Seed unions |
|---|---:|---|---:|---:|---:|
| Bagerhat | 9 | | 77 | 3 | 75 |
| Chuadanga | 4 | | 32 | 4 | 35 |
| Jashore (points: "Jessore") | 8 | | 91 | 8 | 91 |
| Jhenaidah | 6 | | 67 | 6 | 67 |
| Khulna | 9 | Khulna | 70 | 2 | 68 |
| Kushtia | 6 | | 66 | 5 | 67 |
| Magura | 4 | | 36 | 1 | 36 |
| Meherpur | 3 | | 18 | 2 | 18 |
| Narail | 3 | | 38 | 3 | 39 |
| Satkhira | 7 | | 79 | 2 | 78 |
| **Division** | **59** | **1** | **574** | **36** | **574** |

The 574 union points include 5 Sundarbans forest ranges that are not union parishads: Chandpai Range (Mongla), Sharankhola Range (Sharankhola), Khulna Range (Dacope), Nalian Range (Koyra; BBS 2022 puts Nalian Range under Dacope) and Satkhira Range (Shyamnagar). The 2020 points also have 5 metro thanas of Khulna district (`BD4047xx`, level `thana`) and 32 ward points under them.

`boundaries.geojson` (0.88 MB) has 71 polygons: 1 division, 10 districts, 59 upazilas and 1 city corporation (Khulna `BD40473300`). `facts.csv` has 71 `area_km2` values (HDX `area_sqkm`, not official BBS areas). Division 22,584.72 km²; Khulna City Corporation 46.62 km² (seed: 91.315).

Every v03 upazila has a 2020 label point.

## City corporation, metro thanas and wards

- **Khulna City Corporation** has 5 thanas: Daulatpur, Khalishpur, Khan Jahan Ali, Khulna Sadar, Sonadanga.
- **32 ward points = 31 ward numbers** (Ward No-01 … Ward No-31). Ward No-02 is split "(part)" between Daulatpur and Khan Jahan Ali. The ward-to-thana assignment is the same as BBS 2022: Daulatpur 1–6 and 2 (part); Khalishpur 7–15; Khan Jahan Ali 2 (part); Sonadanga 16–20, 25, 26; Khulna Sadar 21–24, 27–31.
- All 32 ward points lie inside the v03 Khulna City Corporation polygon. In the source they hang under the district, not under the city corporation; `areas.csv` keeps them that way.
- Thana label points: Khalishpur, Khulna Sadar and Sonadanga lie inside the city polygon. Daulatpur's lies in Dighalia and Khan Jahan Ali's in Phultala.
- **Three unions are filed under metro thanas:** Aranghata (Daulatpur), Atra Gilatala and Jugipole (Khan Jahan Ali). Their points lie in Dighalia and Phultala.
  - BBS 2022 and the seed list them under Dighalia (Arangghata/Aronghata, Jogipol) and Phultala (Atra Gilatola).
  - They are `unmatched` in the crosswalk because a thana has no seed parent. The same 3 seed unions are `no_source_unit`.

## Crosswalk (`crosswalk.csv`) to `data/seed/geo/admin_areas.csv`

- Districts 10/10 (20020–20029).
- City corporation 1/1: Khulna → 50004.
- Upazilas 59/59:
  - 50 exact.
  - 7 skeleton: Bagharpara, Chaugachha, Jashore Sadar↔Jessore Sadar, Maheshpur↔Moheshpur, Batiaghata↔Botiaghata, Dighalia↔Digholia, Phultala↔Fultola.
  - 2 hand-checked (above).
- Unions 556/574 (96.9 %): 420 high, 118 medium (incl. 7 fuzzy medium such as Kapasadanga↔Karpashdanga, Sardarpur↔Sadarpur, Banshgram↔Bashgram), 18 low. None matched under another upazila.
- 18 HDX unions are unmatched:
  - The 5 forest ranges.
  - The 3 metro-thana unions above.
  - Spelling cases: Howli (seed Hawli), Diara (Dearamodel), S.k.b.(sundarpur) (Sbk), Dacope (Dakop), Lata (Lota), T. S. Bahirdia (Tsb), Sagladah (Chagladoho), Maghi (Moghi), Chanchari (Chacuri), Jagati.
- 18 seed unions have no HDX unit (`no_source_unit`): the counterparts above, plus Panchgram (Kalia), Ailhash (Alamdanga), Raypur and Hasadah (Jibannagar), Bottail (Kushtia Sadar), Dhubail (Mirpur).
- Low-confidence matches to review (18): Maghia↔Moghia, Chandpi↔Chadpai, Khuolia↔Khaulia, Banshtali↔Bastoli, Bhojpatia↔Vospatia, Subha Para↔Subharara, Ganganandapur↔Gangananda, Palsi↔Falsi, Harishankarpur↔Harishongkorpur, Sarappur↔Shorafpur, Aijganti↔Aichgati, Sadipur↔Charsadipur, Gosind Durgapur↔Goswami Durgapur, Bagia↔Bogia, Chaulia↔Chawlia, Bichhali↔Bisali, Diara↔Deara (Kalaroa), Nangalthara↔Langaljhara.
- Paurashavas 0/36: the seed has no Khulna Division pourashavas (36 `no_seed_unit`). They are the same 36 as BBS 2022 and DGHS.
- Thanas (5) and wards (32): `no_seed_level`.

## Cautions

- No Bangla names in the source.
- Apart from the metro-thana cases above, no union or paurashava label point lies outside its own v03 upazila polygon.
- The 2020 points print Jashore as "Jessore" (`district_en` in areas.csv for unions and paurashavas).
- HDX calls ADM4 "not officially confirmed": keep `verified=false`.
