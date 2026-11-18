# HDX COD-AB Bangladesh v03 — Mymensingh Division

- **Source:** https://data.humdata.org/dataset/cod-ab-bgd. Original source BBS; contributed by OCHA ROAP; published by OCHA FIS / HDX.
- **Licence:** CC BY-IGO 3.0.
- **Version:** v03, valid_on 2023-05-21, reviewed 2025-06-01, resource modified 2026-01-26 (same national file as the earlier runs).
- **Run:** `python3 -I data/sources/hdx_cod_ab_bgd/fetch.py --division mymensingh --cache <scratch>` (accessed 2026-11-18). Key `HDX_COD_AB_BGD_MYMENSINGH`, division `mymensingh`, kind `hdx_cod_ab`.
- **No union polygons in v03.** Union (ADM4) codes come from the `bgd_adminpoints` layer (valid_on 2020-11-13). The matching union polygons come from geoBoundaries (`../geoboundaries_bgd_adm4_mymensingh`).
- **Two code schemes:** `HDX_PCODE` (v03, e.g. `BD45614000` Mymensingh City Corporation) and `HDX_PCODE_2020` (2020 points, e.g. `BD45615299` Mymensingh Paurashava).

## fetch.py changes for this run (all off for the earlier divisions)

- `DISTRICT_SEED_BY_DIV["mymensingh"]`: BD4539 Jamalpur, BD4561 Mymensingh, BD4572 Netrokona, BD4589 Sherpur. v03 and
  the 2020 points print "Netrakona"; it pairs with seed Netrokona via the district code.
- No `UNIT_SEED_BY_DIV` entry was needed: the name matcher pairs all 35 upazilas correctly (checked against the seed's
  Bangla names, below).
- **`DIRECTION_WORD_DIVS` is not turned on for Mymensingh:**
  - Neither the 2020 points nor the seed has two unions that differ only by a direction word, so nothing can be crossed.
  - Only three names carry a direction word: Dakshin Maij Para (Dhobaura), Dakshin Bishiura (Netrokona Sadar) and Purbadhala.
  - Tried both ways. With it on, Dakshin Bishiura ↔ seed Dokkhin Bishiura (দক্ষিণ বিশিউড়া) is lost, because the matcher's
    word list has no "Dokkhin". With it off, that pair is made (fuzzy 0.88, medium) and nothing else changes.
- **Rerun check** (Rajshahi with no `--division`; Rangpur, Dhaka, Chattogram, Khulna, Barishal and Sylhet with `--division`, into a scratch folder):
  - areas.csv, boundaries.geojson, facts.csv and both raw files are byte-identical for all seven. The Rangpur crosswalk.csv
    is identical too. Rajshahi's SOURCE.json differs only in `accessed` and the crosswalk checksum.
  - The Rajshahi, Dhaka, Chattogram, Khulna, Barishal and Sylhet crosswalk.csv differ only because the seed changed after
    those folders were built:
    - pourashavas were added;
    - some union rows were re-parented or added, e.g. Sylhet's Madhyanagar unions and Rajshahi's Sukhanpukur, Mandatosh,
      Chak Rajapur and Kayra.
  - The HEAD version of fetch.py on the current seed gives byte-identical output to the new one for all six. No difference comes from the live source.

## Counts

| District (v03) | Upazilas (v03) | City corporations (v03) | Unions (2020 points) | Paurashavas (2020 points) | Seed unions |
|---|---:|---|---:|---:|---:|
| Jamalpur | 7 | | 68 | 6 | 68 |
| Mymensingh | 13 | Mymensingh | 146 | 10 | 146 |
| Netrokona (printed "Netrakona") | 10 | | 86 | 6 | 86 |
| Sherpur | 5 | | 52 | 4 | 52 |
| **Division** | **35** | **1** | **352** | **26** | **352** |

`boundaries.geojson` (0.55 MB) has 41 polygons: 1 division, 4 districts, 35 upazilas and 1 city corporation
(Mymensingh `BD45614000`).
- **Polygons matched to seed ids: 40/40** below the division: 4 districts (20061–20064), 35 upazilas and the city
  corporation (50012). The division polygon is seed 10008; as before, the crosswalk has no division row.
- `facts.csv` has 41 `area_km2` values (HDX `area_sqkm`, not official BBS areas): division 10,512.77 km²; Mymensingh
  4,332.80, Netrakona 2,800.12, Jamalpur 2,051.87, Sherpur 1,327.99; city corporation 99.28 (seed 91.06, `official`).

- **Tarakanda** (v03 `BD45610088`) has no 2020 label point. Its unions are filed under 2020 Phulpur (`BD456181`: 20 union
  points + Phulpur Paurashava).
  - The second pass pairs 9 of them with the seed's Tarakanda unions (`name_exact_other_parent`, medium): Banihala,
    Bishka, Dhakua, Galagaon, Kakni, Kamargaon, Kamaria, Rampur, Tarakanda.
  - The tenth, **Balikhan** (`BD45618112`), stays unmatched; the seed's tenth Tarakanda union is Balikha (বালিখা).
  - These are the 10 unions of BBS 2022 Tarakanda (45-61-88).
- Every other v03 upazila has a 2020 label point.

## City corporation and wards

- **Mymensingh City Corporation** (v03 `BD45614000`, 99.28 km²) → seed 50012.
- The 2020 points have **no thana and no ward points** for the city (the city-corporation row notes this).
- They still carry **Mymensingh Paurashava** (`BD45615299`, under 2020 Mymensingh Sadar). BBS 2022 has no Mymensingh
  Paurashava; it lists the city corporation with 33 wards (`../bbs_census_2022_mymensingh`).

## Crosswalk (`crosswalk.csv`) to `data/seed/geo/admin_areas.csv`

- Districts 4/4 (Netrakona → Netrokona via district code). City corporation 1/1.
- Upazilas 35/35, all agreeing with the seed's Bangla names:
  - 27 exact (incl. Tarakanda, Ishwarganj = Iswarganj, Muktagachha = Muktagacha).
  - 1 banglish: Fulpur ↔ Phulpur (ফুলপুর).
  - 7 skeleton (medium): Bakshiganj ↔ Bokshiganj (বকশীগঞ্জ), Dewanganj ↔ Dewangonj (দেওয়ানগঞ্জ), Melandaha ↔ Melandah
    (মেলান্দহ), Mohanganj ↔ Mohongonj (মোহনগঞ্জ), Netrakona Sadar ↔ Netrokona Sadar (নেত্রকোণা সদর), Nakla ↔ Nokla (নকলা),
    Sreebardi ↔ Sreebordi (শ্রীবরদী).
- Unions 338/352 matched: 233 high, 100 medium, 5 low. The importer uses the 333 high/medium pairs.
- 14 HDX unions are unmatched. Each has a seed union under the same upazila with the same name by Bangla reading (not pinned):
  - Sherpur Sadar: Dhala ~ Dhola (ধলা), Lakshmanpur ~ Losmonpur (লছমনপুর), Char Pakshimari ~ Chorpokhimari (চর পক্ষীমারি),
    Rauha Betmari ~ Rouha (রৌহা).
  - Nalitabari: Poragaon ~ Puraga (পোড়াগাও), Nunni ~ Nonni (নন্নী), Ramchandrakura Mandalia ~ Ramchondrokura (রামচন্দ্রকুড়া).
  - Jhenaigati: Hatibandha Malijhikanda ~ Hatibandha (হাতিবান্দা).
  - Phulpur/Tarakanda: Balikhan ~ Balikha (বালিখা).
  - Kendua: Roailbari ~ Roailbari Amtala (রোয়াইলবাড়ী আমতলা).
  - Atpara: Duaz ~ Duoj (দুওজ), Sonai ~ Shunoi (শুনই).
  - Kalmakanda: Bara Kharpan ~ Borokhapon (বড়খাপন).
  - Netrokona Sadar: Lakshmiganj ~ Lokkhiganj (লক্ষীগঞ্জ).
- The 14 seed unions with no HDX unit are exactly these counterparts.
- Low pairs to review (all agree with the seed's Bangla name): Nilakshmia ↔ Nilakhia (নিলক্ষিয়া, Bokshiganj), Rajai ↔ Rajoi
  (রাজৈ, Bhaluka), Baira (kewatkhali) ↔ Boyra (বয়ড়া, Mymensingh Sadar), Barkashia Biramp ↔ Borokashia Birampur
  (বড়কাশিয়া বিরামপুর, Mohongonj), Marichpura ↔ Morichpuran (মরিচপুরাণ, Nalitabari).
- Paurashavas 0/26: the seed has no Mymensingh Division pourashavas (`no_seed_unit`).
- The 2020 paurashava list vs BBS 2022 (27):
  - not in the 2020 points: Bakshiganj, Haluaghat and Hazrabari;
  - only in the 2020 points: Mymensingh and Purbadhala.

## Cautions

- No Bangla names in the source.
- The 2020 points print some names differently: "Netrakona", "Gaffargaon", "Gauripur", "Phulpur" (v03 "Fulpur"),
  "Melandaha", "Nakla", "Sreebardi", "Bakshiganj", "Mohanganj".
- HDX calls ADM4 "not officially confirmed": keep `verified=false`.
- The 2020 points predate Tarakanda upazila and the city corporation's wards; use BBS 2022 for those.
