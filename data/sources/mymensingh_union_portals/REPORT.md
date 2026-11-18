# Union Parishad portals of Mymensingh Division

- **Collector:** `rajshahi_union_portals/fetch.py --division mymensingh`.
- **Union list:**
  - the DC portal lists for all four districts;
  - Mymensingh District:
    - Haluaghat, which mymensingh.gov.bd gives no upazila cell, comes from the national portal's list of union portals (bangladesh.gov.bd/views/union-list).
    - জুগলী, printed under Tarakanda, is dropped because the national list has it under Haluaghat.
    - Gouripur (DC 8), Phulpur (DC 6) and Tarakanda (DC 9 after the drop) also come from the national list (10 each).
  - total 351.
- **Portal links:**
  - from the DC lists (Netrokona only, 77);
  - else from the national list (255, `portal_link_from` in `raw/coverage.csv`, or the national list itself for the four upazilas above);
  - else from the upazila portals' union pages (3);
  - none: 16.
- Each portal → menu item "এক নজরে" → label matcher.
- Only robots.txt, the home page and the এক নজরে page are fetched per union. 8 parallel workers on different hosts, at least 1.2 s per host. 929 requests in about 2 minutes (first run). Accessed 2026-11-18.

| Status | Unions |
|---|---|
| ok | 256 |
| no এক নজরে menu item | 65 |
| no portal link found | 16 |
| empty page | 11 |
| page error (HTTP 404: মাঘান সিয়াদার, চাকুয়া, হোগলা) | 3 |

| District | Unions | ok | From national list |
|---|---|---|---|
| Mymensingh | 145 | 106 | 42 (Haluaghat, Gouripur, Phulpur, Tarakanda) |
| Jamalpur | 68 | 50 | 0 |
| Sherpur | 52 | 43 | 0 |
| Netrokona | 86 | 57 | 0 |

- **areas.csv (351):** one row per union.
  - `website` only when the portal answered (332).
  - `name_en` for Sherpur's 52, as printed on the DC list.
  - `source_url` is the এক নজরে page, or the list when there is none.
  - DOUBT notes where the portal title does not repeat the list's spelling:
    - হরিরামপুর (title "রামপুর ইউনিয়ন");
    - রসুলপুর and বারবাড়ীয়া (both "Rasulpur Union");
    - বালিয়া (English title);
    - বকশীগঞ্জ/বকসীগঞ্জ, পার্থশী/পাথশী, গোসাইপুর/গোশাইপুর, বাউসী/বাউশী, গোবিন্দশ্রী/গেবিন্দশ্রী.
- **facts.csv (393):**
  - population 90, villages 87, mouzas 82, area km² 60, households 35, wards 14;
  - area in other units: unstated 9, sq miles 8, acres 8;
  - 4 values flagged DOUBT: area 6,712 km² (পাইথল, লংগাইর), area 7,434.96 km² (কামারগাঁও), population 309,729 (বানিহালা).

## Caveats

- **351 rows against 352 seed unions (registry 351):** Mymensingh 145 against the seed's 146 (Mymensingh Sadar 11 against 13; Nandail 13 against 12).
- **16 unions without a portal link:** spelling variants the registry spells differently, e.g. চরঈশ্বদিয়া, বাকতা, উত্থুরা, ধনুয়া কামালপুর, নুরূন্দি, তিতপল্যা, তুলসীরচর, করইচরা, ঝিনাইগাতী সদর, রামচন্দ্রকুড়া মন্ডলিয়াপাড়া. Links were not guessed.
- **Old pages:** population years printed: 2001 ×9, 2011 ×7, 2015 ×2, 2022 ×1; 71 give none. Prefer BBS 2022.
- **Raw texts:** `raw/*_glance.txt` have phone numbers and e-mails redacted. 19 এক নজরে pages that list people (members, mobiles) are used for figures only; their text is not saved (`raw` column in coverage.csv).

## Licence

No licence stated; facts only. Attribution: ইউনিয়ন পরিষদ পোর্টাল, ময়মনসিংহ বিভাগ — জাতীয় তথ্য বাতায়ন (<union>.<district>.gov.bd). The national list is from the Bangladesh National Portal (bangladesh.gov.bd).
