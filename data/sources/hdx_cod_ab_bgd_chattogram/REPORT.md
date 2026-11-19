# HDX COD-AB Bangladesh v03 — Chattogram Division

- **Source:** https://data.humdata.org/dataset/cod-ab-bgd. Original source BBS; contributed by OCHA ROAP; published by OCHA FIS / HDX.
- **Licence:** CC BY-IGO 3.0.
- **Version:** v03, valid_on 2023-05-21, reviewed 2025-06-01, resource modified 2026-01-26 (same national file as the earlier runs).
- **Run:** `python3 -I data/sources/hdx_cod_ab_bgd/fetch.py --division chattogram` (accessed 2026-11-17). Key `HDX_COD_AB_BGD_CHATTOGRAM`, division `chattogram`, kind `hdx_cod_ab`.
- **No union polygons in v03.** Union (ADM4) codes come from the `bgd_adminpoints` layer (valid_on 2020-11-13). The matching union polygons come from geoBoundaries (`../geoboundaries_bgd_adm4_chattogram`).
- **Two code schemes:** `HDX_PCODE` (v03, e.g. `BD20151600` Chattogram City Corporation) and `HDX_PCODE_2020` (2020 points, e.g. `BD201541` Kotwali thana, `BD20154131` Ward No-31).

## fetch.py changes for this run (all off for the earlier divisions)

- `DISTRICT_SEED_BY_DIV["chattogram"]`: hand-checked district P-codes. All 11 names are identical to the seed.
- `UNIT_SEED_BY_DIV["chattogram"]`: four upazilas the name matcher could not pair, or paired wrongly, checked against the seed's Bangla names (method `code_hand_checked`). Without them, the fuzzy tier paired Matlab **Uttar** with seed Matlab **South**.
  - Matlab Dakkhin → Matlab South (মতলব দক্ষিণ, 30056)
  - Matlab Uttar → Matlab North (মতলব উত্তর, 30058)
  - Adarsha Sadar → Comilla Sadar (কুমিল্লা সদর, 30011)
  - Sadar Dakkhin → Sadarsouth (সদর দক্ষিণ, 30014)
- Direction words for unions (`DIRECTION_WORD_DIVS`):
  - Uttar/Dakshin(/Dakkhin)/Purba/Paschim are read as North/South/East/West and taken out before comparing names. This also applies when the word is glued to the name (Purbagujra, Uttarhowla, Chitoshiwest).
  - A pair whose directions differ is never matched.
  - A pair where only one side carries a direction is at most `low`, and only allowed when the rest of the name is unique on both sides. So Paschim/Purba Rupasdi against a single seed Rupushdi stays unmatched.
  - 112 matched unions carry a "direction word read as …" note.
- Rajshahi/Rangpur/Dhaka reruns into a scratch folder:
  - areas, boundaries, facts and raw files: identical; the Rangpur crosswalk is identical too.
  - Rajshahi and Dhaka `crosswalk.csv` differ only in pourashava rows. This is because the seed gained pourashavas after those folders were built: the HEAD version of fetch.py on the current seed gives the same output as the new one.

## Counts

| District | Upazilas (v03) | City corporations (v03) | Unions (2020 points) | Paurashavas (2020 points) | Seed unions |
|---|---:|---|---:|---:|---:|
| Bandarban | 7 | | 30 | 2 | 31 |
| Brahmanbaria | 9 | | 100 | 4 | 100 |
| Chandpur | 8 | | 88 | 7 | 88 |
| Chattogram | 15 | Chattogram | 197 | 10 | 196 |
| Cox's Bazar | 9 | | 71 | 4 | 69 |
| Cumilla | 17 | Cumilla | 188 | 10 | 192 |
| Feni | 6 | | 43 | 5 | 43 |
| Khagrachhari | 9 | | 38 | 3 | 36 |
| Lakshmipur | 5 | | 58 | 4 | 57 |
| Noakhali | 9 | | 91 | 8 | 89 |
| Rangamati | 10 | | 49 | 2 | 49 |
| **Division** | **104** | **2** | **953** | **59** | **950** |

The 2020 points also have 11 metro thanas of Chattogram district (`BD2015xx`, level `thana`, district printed "Chittagong") and 51 ward points under them.

`boundaries.geojson` (1.25 MB) has 118 polygons: 1 division, 11 districts, 104 upazilas and 2 city corporations (Chattogram `BD20151600`, Cumilla `BD20195000`). `facts.csv` has 118 `area_km2` values (HDX `area_sqkm`, not official BBS areas). Division 32,833.08 km²; Chattogram City Corporation 198.54; Cumilla City Corporation 52.31.

Four v03 upazilas have no 2020 label point (they were created later): Karnaphuli, Eidgaon, Lalmai, Guimara.

## City corporations, metro thanas and wards

- **Chattogram City Corporation:**
  - 11 thanas (Bayejid Bostami, Bakalia, Chandgaon, Chittagong Port, Double Mooring, Halishahar, Kotwali, Khulshi, Pahartali, Panchlaish, Patenga) and 51 ward points: 41 ward numbers (Ward No-01 … Ward No-41), 10 of them split between two thanas as "(Part)".
  - All 62 points lie inside the v03 Chattogram City Corporation polygon. In the source they hang under the district, not under the city corporation; `areas.csv` keeps them that way.
  - The numbering 1–41 matches the 41 city wards of BBS 2022. The 2020 points lack the 4 newer thanas that BBS 2022 has (Akbarshah, Chalk Bazar, EPZ, Sadarghat).
- **Cumilla City Corporation:**
  - No thana or ward points.
  - Inside its v03 polygon lie the label points of the former Comilla Paurashava (Adarsha Sadar) and Comilla Dakshin Paurashava (Sadar Dakshin), which the city corporation replaced in 2011. Both are kept as paurashavas, as printed.

## Crosswalk (`crosswalk.csv`) to `data/seed/geo/admin_areas.csv`

- Districts 11/11 (20001–20011).
- City corporations 2/2: Chattogram → 50003, Cumilla → 50009.
- Upazilas 104/104:
  - 88 exact, 3 banglish, 8 skeleton.
  - 1 fuzzy (medium): Lakkhichhari↔Laxmichhari.
  - 4 hand-checked (above).
- Unions 883/953 (92.7 %): 624 high, 214 medium, 45 low; 1 matched under another upazila (Bhaibonchhara: HDX Khagrachhari Sadar, seed Mohalchari). 70 HDX unions are unmatched; 67 seed unions have no HDX unit (`no_source_unit`).
- Paurashavas 0/59: the seed has no pourashava rows in Chattogram Division (56 `no_seed_unit`; Matlab, Comilla and Comilla Dakshin Paurashava are `unmatched` because of their parent).
- Thanas (11) and wards (51): `no_seed_level`.

HDX unions left unmatched, by upazila:
- Akhaura: Dakshin/Uttar Akhaura.
- Banchharampur: 8 Dakshin/Uttar/Purba/Paschim unions (the seed has plain names).
- Brahmanbaria Sadar: Dakshin/Uttar Natai (the seed has "Natai" twice).
- Nabinagar: Paschim/Purba Nabinagar (seed Nabinagare/Nabinagarw).
- Shahrasti: Tamta Paschim/Purba (seed Tamta North/South).
- Comilla Sadar Dakshin: Baghmara, Belghar, Purba/Paschim Jorekaran.
- Comilla Adarsha Sadar: Kalir Bazar (Dakshin/Uttar).
- Debidwar: Isab Pur, Debidwar, Uttar/Dakshin Dhamti.
- Chandina: 2 unions with bracketed aliases.
- Rangunia: Chandraghona Kadamtali, Padua, Rangunia.
- Fatikchhari: Dhurung, Khiram, Rangamatia.
- Hatiya: Chandnandi, Harni, Tamaruddin.
- Chauddagram: Chauddagram, Ujirpur.
- Nangalkot: Jodda, Nangalkot.
- Manoharganj: Khila, Lakshmanpur, Uttar Hawla.
- Single unions elsewhere: Tankabati, Ghandung, St.Martin Dwip, Patali Machhuakhali, Purba Barabheola, Lakhyarchar, Dakshin Dhurung, Sakhua, Karaia, Sanua, Baksh Mohammad, Torabgang, Mandari, Uttar Joypur, Char Alexandar, Beimar, Sindukchari, Ulta Chari, Digghapar, Dharmapur, Homna Union, Kanalla, Dhar Mandal, Deora, Paschim/Purba Baluthupa.

Seed unions with no HDX counterpart:
- Duplicates in the seed: Karnafuli's five unions (also listed under Patiya), and Lalmai's eight Bagmara/Bhuloin/Belgor/Perul unions (also listed under Sadarsouth).
- Truncated seed names: Akhauran/Akhauras, Nabinagare/Nabinagarw, Talshaharw.
- The rest are the counterparts of the HDX names above.

Low-confidence matches to review (`confidence=low`, 45). They include:
- Silkup↔Silk, Laksam↔Laksam Purba, Padua↔Podua, Nhilla↔Hnila.
- Uttar/Dakshin Hamchadi↔Hamsadi (North/South), Paschim Panchgachhia↔West Passgacia.
- One-sided direction pairs such as Uttar Payalgachha↔Payalgacha, Uttar Daudkandi↔Daudkandi, Purba Talsahar↔Talsahar.

## Cautions

- No Bangla names in the source.
- Label points outside their own v03 upazila polygon (besides the Cumilla city-corporation case above):
  - The new upazilas: 7 Comilla Sadar Dakshin unions and Bakai (Laksam) lie in Lalmai; 5 Patiya unions in Karnaphuli; 5 Cox's Bazar Sadar unions in Eidgaon; Beimar, Hapchhari and Sindukchari in Guimara.
  - Hill-district border cases: Amtali (Baghai Chhari) in Langadu; Rupakari in Dighinala; Kamalchhari and Khagrachhari union in Mahalchhari; Khagrachhari Paurashava in Matiranga; Latiban in Khagrachhari Sadar; Mahalchhari union in Naniarchar; Pathachhara in Manikchhari.
  - Others: Char Gazi (Ramgati) in Subarnachar, Mohammadpur (Subarnachar) in Hatiya, Tamta Paschim (Shahrasti) in Hajiganj.
  - Azimpur and Urirchar (Sandwip) lie in no upazila polygon.
- HDX calls ADM4 "not officially confirmed": keep `verified=false`.
