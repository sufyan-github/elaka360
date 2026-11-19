# HDX COD-AB Bangladesh v03 — Barishal Division

- **Source:** https://data.humdata.org/dataset/cod-ab-bgd. Original source BBS; contributed by OCHA ROAP; published by OCHA FIS / HDX.
- **Licence:** CC BY-IGO 3.0.
- **Version:** v03, valid_on 2023-05-21, reviewed 2025-06-01, resource modified 2026-01-26 (same national file as the earlier runs).
- **Run:** `python3 -I data/sources/hdx_cod_ab_bgd/fetch.py --division barishal --cache <scratch>` (accessed 2026-11-18). Key `HDX_COD_AB_BGD_BARISHAL`, division `barishal`, kind `hdx_cod_ab`.
- **No union polygons in v03.** Union (ADM4) codes come from the `bgd_adminpoints` layer (valid_on 2020-11-13). The matching union polygons come from geoBoundaries (`../geoboundaries_bgd_adm4_barishal`).
- **Two code schemes:** `HDX_PCODE` (v03, e.g. `BD10065000` Barishal City Corporation) and `HDX_PCODE_2020` (2020 points, e.g. `BD10065101` Ward No-01).

## fetch.py changes for this run (all off for the earlier divisions)

- `DISTRICT_SEED_BY_DIV["barishal"]`: hand-checked district P-codes. Five names equal the seed; HDX "Jhalokati" (BD1042) = seed Jhalokathi.
- `UNIT_SEED_BY_DIV["barishal"]`: Indurkani BD10790090 → seed Zianagar (জিয়ানগর, 30245), method `code_hand_checked`.
  - No name tier pairs them: the seed's Bangla name is the upazila's former name.
  - HDX's own 2020 point for this upazila (BD107990) is named Zianagar (see the areas.csv note).
  - The seed's three Zianagar unions are Indurkani's 2020 union points Bali Para, Parerhat, Pattashi.
  - Without the pin, those 3 unions had no parent.
- `DIRECTION_WORD_DIVS` now includes `barishal`.
  - Without it, the fuzzy tier paired Uttar Joynagar with seed **South** Joy Nagar and Uttar Sakuchia with **South** Sakuchia.
  - With it, 8 unions match with a "direction word read as …" note: Paschim Illisha ↔ Westilisa, Uttar/Dakshin Dighaldi ↔ North/South Digholdi, Uttar/Dakshin Joynagar ↔ North/South Joy Nagar, Uttar/Dakshin Sakuchia ↔ North/South Sakuchia, Paschim Char Umed.
  - One more is low on one side only: Purba Deulbaridobra ↔ Daulbari Dobra.
- Rajshahi (no `--division`)/Rangpur/Dhaka/Chattogram/Khulna reruns into a scratch folder:
  - areas, boundaries, facts and raw files: identical for all five; the Rangpur crosswalk is identical too.
  - Rajshahi, Dhaka, Chattogram and Khulna `crosswalk.csv` differ only because the seed gained pourashavas (and some unions, e.g. Sukhanpukur, Garaitupi) after those folders were built. The HEAD version of fetch.py on the current seed gives the same output as the new one.

## Counts

| District (v03) | Upazilas (v03) | City corporations (v03) | Unions (2020 points) | Paurashavas (2020 points) | Seed unions |
|---|---:|---|---:|---:|---:|
| Barguna | 6 | | 42 | 4 | 43 |
| Barishal (points: "Barisal") | 10 | Barishal | 85 | 5 | 85 |
| Bhola | 7 | | 68 | 5 | 64 |
| Jhalokati | 4 | | 32 | 2 | 32 |
| Patuakhali | 8 | | 70 | 4 | 72 |
| Pirojpur | 7 | | 51 | 3 | 52 |
| **Division** | **42** | **1** | **348** | **23** | **348** |

`boundaries.geojson` (0.38 MB) has 50 polygons: 1 division, 6 districts, 42 upazilas and 1 city corporation (Barishal `BD10065000`). `facts.csv` has 50 `area_km2` values (HDX `area_sqkm`, not official BBS areas). Division 12,693.47 km²; Barishal City Corporation 58.5 km² (seed: 58.0).

- **Taltali and Rangabali** are v03 upazilas with no 2020 label point (created after the 2020 list). Their unions are filed under the 2020 parents:
  - Amtali: Barabagi, Chhota Bagi, Karaibaria, Nishanbaria, Pancha Koralia, Sarikkhali, Sonakata.
  - Galachipa: Bara Baisdia, Chalitabunia, Char Montaz, Chhota Baisdia, Rangabali.
  - These 12 points lie inside the v03 Taltali/Rangabali polygons.
  - 11 of them match the seed's Taltali/Rangabali unions in the second pass (`*_other_parent`: 8 medium, 3 low).
- **Paurashavas:** the 23 points are all named just "Paurashava". BBS 2022 has 26; there is no point for Ujirpur, Bhandaria or Kuakata.

## City corporation and wards

- **Barishal City Corporation**: the 2020 points have no thana for the city. The 30 ward points (Ward No-01 … Ward No-30, none split) are filed under the 2020 upazila "Barisal Sadar (Kotwali)" (BD100651 = v03 Barishal Sadar upazila BD10060051).
- All 30 lie inside the v03 city-corporation polygon. `areas.csv` keeps them under the upazila, as printed. The 30 ward numbers equal the 30 city wards of BBS 2022.
- Crosswalk: `no_seed_level` (the seed has no ward level).

## Crosswalk (`crosswalk.csv`) to `data/seed/geo/admin_areas.csv`

- Districts 6/6 (20030–20035). City corporation 1/1: Barishal → 50007.
- Upazilas 42/42:
  - 32 exact.
  - 6 skeleton: Patharghata↔Pathorghata, Gaurnadi↔Gournadi, Ujirpur↔Wazirpur, Charfasson↔Charfesson, Daulatkhan↔Doulatkhan, Jhalokathi Sadar↔Jhalakathi Sadar.
  - 1 banglish: Hijla↔Hizla.
  - 2 fuzzy medium: Borhanuddin↔Borhan Sddin, Kanthalia↔Kathalia.
  - 1 hand-checked (above).
  - All agree with the seed's Bangla names.
- Unions 335/348 matched: 221 high, 101 medium, 13 low. The importer uses the 322 high/medium.
- 13 HDX unions unmatched:
  - Agarpur.
  - Dehergati (seed Deherhoti).
  - Baisari Para (Baishari).
  - Shikarpur (Shikerpur Wazirpur).
  - Gangapur, Hassan Nagar, Sachra, Tabgi (Borhanuddin; not in the seed).
  - Bara Malancha.
  - Baga (Boga).
  - Kalyankalas, Khaprabhanga.
  - Chira Para Parsaturia (Chirapara).
- 13 seed unions have no HDX unit: Boga, Sreerampur, Mahipur, Champapur, Kalagachhia, Kolardoania, Chirapara, Jahangir Nagar, Deherhoti, Shikerpur Wazirpur, Baishari, Baro Molongchora, Chhotabagi (Taltali).
- **Doubtful:** HDX Chhota Bagi (point in Taltali's polygon, 2020 parent Amtali) is paired at medium with seed Chotobogi under **Amtali** (42398). The seed also has Chhotabagi under Taltali (42432), which is probably the right unit; the seed seems to hold this union twice.
- Low-confidence matches to review (13): Gaila↔Goila, Char Kowa↔Charcowa, Mehendiganj↔Mehendigong, Char Shibpur↔Shibpur, Adhakha Nazrul Nagar↔Nazrulnagar, Char Kukri Mukri↔Kukrimukri, Medua↔Madua, Baruia↔Baraia, Gulishakhali↔Haltagulishakhali, Purba Deulbaridobra↔Daulbari Dobra, Karaibaria↔Karibaria, Bara Baisdia↔Barobaisdia, Chhota Baisdia↔Chattobaisdia.
- Paurashavas 0/23: the seed has no Barishal Division pourashavas (`no_seed_unit`). Wards (30): `no_seed_level`.

## Cautions

- No Bangla names in the source.
- The 2020 points print Barishal as "Barisal" (`district_en` for unions, paurashavas and wards).
- HDX calls ADM4 "not officially confirmed": keep `verified=false`.
