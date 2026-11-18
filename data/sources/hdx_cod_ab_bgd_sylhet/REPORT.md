# HDX COD-AB Bangladesh v03 — Sylhet Division

- **Source:** https://data.humdata.org/dataset/cod-ab-bgd. Original source BBS; contributed by OCHA ROAP; published by OCHA FIS / HDX.
- **Licence:** CC BY-IGO 3.0.
- **Version:** v03, valid_on 2023-05-21, reviewed 2025-06-01, resource modified 2026-01-26 (same national file as the earlier runs).
- **Run:** `python3 -I data/sources/hdx_cod_ab_bgd/fetch.py --division sylhet --cache <scratch>` (accessed 2026-11-18). Key `HDX_COD_AB_BGD_SYLHET`, division `sylhet`, kind `hdx_cod_ab`.
- **No union polygons in v03.** Union (ADM4) codes come from the `bgd_adminpoints` layer (valid_on 2020-11-13). The matching union polygons come from geoBoundaries (`../geoboundaries_bgd_adm4_sylhet`).
- **Two code schemes:** `HDX_PCODE` (v03, e.g. `BD60915000` Sylhet City Corporation) and `HDX_PCODE_2020` (2020 points, e.g. `BD60916201` Ward No-01).

## fetch.py changes for this run (all off for the earlier divisions)

- `DISTRICT_SEED_BY_DIV["sylhet"]`: BD6036 Habiganj, BD6058 Moulvibazar, BD6090 Sunamganj, BD6091 Sylhet. The v03 names
  equal the seed; the 2020 points print "Maulvibazar".
- New table `UPAZILA_RECODED_BY_DIV` (2020 point P-code → v03 P-code, for an upazila renamed **and** recoded since 2020).
  Sylhet: `BD609027` Dakshin Sunamganj → `BD60900087` Shantiganj.
  - The 2020 code ends in 27 and the v03 code in 87, so the old rule (same last two digits) did not pair them.
  - Without the table:
    - the 2020 point was written as a city `thana`;
    - its 8 union points had no upazila;
    - the city-corporation note wrongly said the city had thana points.
  - All 8 union points of BD609027 (Durgapasha, Joykalas, Paschim/Purba Birgaon, Paschim/Purba Pagla, Patharia,
    Shimulbak) lie inside the v03 Shantiganj polygon. BBS 2022 60-90-87 Shantiganj has the same 8 unions.
  - The v03 upazila row notes "2020 P-code BD609027 (Dakshin Sunamganj); renamed and recoded since 2020 (same unions; hand-checked)".
- `UNIT_SEED_BY_DIV["sylhet"]`: Shantiganj BD60900087 → seed **South Sunamganj** (দক্ষিণ সুনামগঞ্জ, 30301), method
  `code_hand_checked`.
  - The seed's Bangla name is the upazila's former name.
  - The seed's 8 South Sunamganj unions are the 8 unions above.
  - No name tier pairs them.
- `DIRECTION_WORD_DIVS` now includes `sylhet`.
  - 35 union pairs carry a "direction word read as …" note. Examples: Purba/Paschim Bara Bhakhair ↔ Barabhakoir
    Purba/Paschim; Uttar/Dakshin Sukhair Rajapur ↔ Sukhair Rajapur North/South; Uttar/Dakshin Bangshikunda ↔
    Bongshikunda North/South; Uttar/Dakshin Khurma ↔ Khurma North/South.
  - Four of the 35 are low, with the direction word on one side only (below).
  - The seed also spells directions "Uttor", "Purbo", "Pashim" and "Dakkin". The matcher's word list was not changed, so
    the earlier divisions stay the same; these unions stay unmatched (listed below).
- Rajshahi (no `--division`), Rangpur, Dhaka, Chattogram, Khulna and Barishal were rerun into a scratch folder:
  - areas.csv, boundaries.geojson, facts.csv and both raw files are byte-identical for all six; the Rangpur crosswalk.csv is identical too.
  - The Rajshahi, Dhaka, Chattogram, Khulna and Barishal crosswalk.csv differ only because the seed gained pourashavas
    after those folders were built: their pourashava rows now read `unmatched` instead of `no_seed_unit`.
  - On the current seed, the HEAD version of fetch.py gives byte-identical output to the new one for all six.

## Counts

| District (v03) | Upazilas (v03) | City corporations (v03) | Unions (2020 points) | Paurashavas (2020 points) | Seed unions |
|---|---:|---|---:|---:|---:|
| Habiganj | 9 | | 77 | 6 | 78 |
| Moulvibazar (points: "Maulvibazar") | 7 | | 67 | 5 | 67 |
| Sunamganj | 12 | | 87 | 4 | 87 |
| Sylhet | 13 | Sylhet | 102 | 4 | 104 |
| **Division** | **41** | **1** | **333** | **19** | **336** |

`boundaries.geojson` (0.68 MB) has 47 polygons: 1 division, 4 districts, 41 upazilas and 1 city corporation (Sylhet
`BD60915000`). **Polygons matched to seed ids: 46/46** below the division: 4 districts (20036–20039), 41 upazilas and the city
corporation (50006). The division polygon is seed 10005; as before, the crosswalk has no division row. `facts.csv` has 47
`area_km2` values (HDX `area_sqkm`, not official BBS areas). The division is 12,373.31 km².

- **Upazilas without a 2020 label point:** Osmaninagar, Shayestaganj, Madhyanagar and Shantiganj. Shantiganj is the
  recoded Dakshin Sunamganj (above). The others' union points are filed under their 2020 parents and lie inside the v03 polygons:
  - Osmaninagar: Burunga, Dayamir, Goula Bazar, Omarpur, Osmanpur, Paschim Pailanpur, Sadipur, Tajpur (2020 parent Balaganj).
  - Shayestaganj: Nurpur, Saistaganj and "Shayestagang Paurashava" (2020 parent Habiganj Sadar).
  - Madhyanagar: Chamardani, Dakshin Bongshikunda, Madhyanagar, Uttar Bangshikunda (2020 parent Dharampasha).
- How these match in the crosswalk:
  - The second pass pairs 7 Osmaninagar unions and both Shayestaganj unions with the seed (`*_other_parent`: 3 medium, 6 low).
  - Burunga stays unmatched (seed Burungabazar).
  - The 4 Madhyanagar unions pair with seed unions under **Dharmapasha**, where the seed keeps them. Seed Madhyanagar (30493) has no unions.
- **Paurashavas:** 19 points. BBS 2022 has 20; there is no point for Bishwanath.

## City corporation and wards

- **Sylhet City Corporation** (v03 BD60915000, HDX area 27.05 km²; the seed has 79.5 km², `official`). The 2020 points
  have no thana for the city.
- The 27 ward points (Ward No-01 … 27) are filed under the 2020 upazila Sylhet Sadar (BD609162 = v03 BD60910062).
  - All 27 lie inside the v03 city-corporation polygon.
  - `areas.csv` keeps them under the upazila, as printed.
  - The 27 ward numbers equal the 27 city wards of BBS 2022.
- Crosswalk: `no_seed_level` (the seed has no ward level).

## Crosswalk (`crosswalk.csv`) to `data/seed/geo/admin_areas.csv`

- Districts 4/4. City corporation 1/1: Sylhet → 50006.
- Upazilas 41/41, all agreeing with the seed's Bangla names:
  - 35 exact.
  - 3 skeleton: Baralekha↔Barlekha (বড়লেখা), Kamalganj↔Kamolganj (কমলগঞ্জ), Jaintapur↔Jaintiapur (জৈন্তাপুর).
  - 1 banglish: Bishwambharpur↔Bishwambarpur.
  - 1 fuzzy medium: Dakkhin Surma↔Dakshinsurma (দক্ষিণ সুরমা).
  - 1 hand-checked: Shantiganj.
- Unions 311/333 matched: 211 high, 84 medium, 16 low. The importer uses the 295 high/medium pairs.
- 22 HDX unions unmatched (seed counterpart by Bangla name in brackets where clear):
  - Uttar Purba / Uttar Paschim / Dakshin Purba / Dakshin Paschim Baniachang (seed Baniachong North East / North West /
    South East / South West). The matcher does not compare names with two direction words.
  - Uttarbhag (Uttorbhag উত্তরভাগ).
  - Ranikhai Uttar (Uttor Ronikhai উত্তর রনিখাই).
  - Paschim Lakshmip Rasad / Purba Lakshmi Prasad (Lakshiprashad Pashim / Purbo).
  - Purba Dighirpar (Digirpar Purbo দিঘিরপার পূর্ব).
  - Paschim Dighirpar: no counterpart in the seed or in BBS 2022.
  - Dhaka Dakshin (Dhakadakshin ঢাকাদক্ষিন).
  - Bagha: not in the seed; BBS 2022 has it.
  - Saidergaon (seed Gobindganj-Syedergaon গোবিন্দগঞ্জ-সৈদেরগাঁও; BBS prints "Gobindganj Saidergaon").
  - Haldipur and Syed Pur (seed Chilaura Holdipur, Syedpur Shaharpara; BBS prints the long names). Probably the same.
  - Sulla (seed Shalla Sadar শাল্লা সদর).
  - Dakshin / Uttar Badal (seed Bordal South / North বড়দল দক্ষিণ / উত্তর).
  - Boaljur Bazar (Boaljur বোয়ালজুর).
  - Burunga (Burungabazar বুরুঙ্গাবাজার).
  - Khazanchigaon (Khajanchi খাজাঞ্চী).
  - Beani Bazar: no BBS 2022 or seed union of that name; not paired.
- 25 seed unions have no HDX unit: the counterparts above, plus Uttar Kushiara and Uttar Fenchuganj (Fenchuganj has only
  3 union points in 2020; the seed and BBS have 5), Daubari, Kamalbazar and Brahmandura.
- **Doubtful (low; direction word on one side only):**
  - Dakshin Islampur↔Islampur (BBS prints "Islampur").
  - Dakshin Dowarabazar↔Dowarabazar.
  - Uttar Badaghat↔Badaghat (the seed also has Badaghat South).
  - Amura↔West Amura (BBS prints "Paschim Amura").
- Other low pairs to review: Mirahi↔Mirashi, Bamai↔Bamoi, Andiurauk↔Andiura, Paniunda↔Paniumda, Chandighat↔Chadnighat,
  Kajalshar↔Kajalshah, and the six low `*_other_parent` pairs.
- Paurashavas 0/19: the seed has no Sylhet Division pourashavas (`no_seed_unit`). Wards (27): `no_seed_level`.

## Cautions

- No Bangla names in the source.
- The 2020 points print some names differently: "Maulvibazar", "Golabganj", "Dharampasha", "Sulla", "Beani Bazar",
  "Maulvi Bazar Sadar".
- HDX calls ADM4 "not officially confirmed": keep `verified=false`.
- The v03 city-corporation polygon (27.05 km², 27 wards) does not match the seed's official 79.5 km². Do not use it as
  the city's current extent.
