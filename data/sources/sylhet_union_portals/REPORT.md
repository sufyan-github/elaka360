# Union Parishad portals of Sylhet Division

- **Collector:** `rajshahi_union_portals/fetch.py --division sylhet`.
- **Union list:**
  - the DC portal lists for all four districts;
  - Sunamganj's Jamalganj comes from the national portal's list of union portals (bangladesh.gov.bd/views/union-list): the DC list names 5, the national list 6;
  - Dharmapasha: the DC list (6) is kept against the national list's 10. The national list still has Madhyanagar's 4 unions under Dharmapasha and none under Madhyanagar, which the DC list names with 4;
  - total 339.
- **Portal links:**
  - from the DC lists (Sylhet only, 102);
  - else from the national list (200, `portal_link_from` in `raw/coverage.csv`);
  - else from the upazila portals' union pages (1).
- Each portal → menu item "এক নজরে" → label matcher.
- Only robots.txt, the home page and the এক নজরে page are fetched per union. 8 parallel workers on different hosts, at least 1.2 s per host. 898 requests in about 2 minutes. Accessed 2026-11-18.

| Status | Unions |
|---|---|
| ok | 259 |
| no এক নজরে menu item | 46 |
| no portal link found | 30 |
| empty page (শরীফপুর, ফুলতলা, ছৈলা-আফজলাবাদ) | 3 |
| page error (HTTP 404, জলসুখা) | 1 |

| District | Unions | ok | From national list |
|---|---|---|---|
| Sylhet | 106 | 86 | 0 |
| Moulvibazar | 67 | 58 | 0 |
| Habiganj | 78 | 48 | 0 |
| Sunamganj | 88 | 67 | 6 (Jamalganj) |

- **areas.csv (339):** one row per union.
  - `website` only when the portal answered (307).
  - `source_url` is the এক নজরে page, or the list when there is none.
  - DOUBT notes:
    - the portal title does not repeat the list's spelling: গোলাপগঞ্জ and ফুলবাড়ি (English titles), চারখাই/চরখাই, উছমানপুর/উসমানপুর, শমসেরনগর/শমশেরনগর, and লক্ষীপ্রসাদ পূর্ব ("Site is not available");
    - the national list places নূরপুর and শায়েস্তাগঞ্জ (Habiganj Sadar) under Shayestaganj, and মধ্যনগর under Dharmapasha;
    - পশ্চিম গেীরীপুর is malformed.
- **facts.csv (530):**
  - villages 123, population 122, mouzas 120, area km² 79, households 51, wards 11;
  - area in other units: acres 11, sq miles 9, hectares 2, unstated 2;
  - 3 values flagged DOUBT: area 8,694 and 12,608 "বর্গ কি.মি." for হাটখোলা and আশারকান্দি; population 203,371 for মনুমুখ.
  - লেঙ্গুঁড়া's "১৬, ৫৫৫ জন" is read as 16,555 (noted).

## Caveats

- **339 rows vs 336 seed unions (registry 337):**
  - Habiganj 78 (seed 78): নূরপুর and শায়েস্তাগঞ্জ are printed twice on the DC list, and Ajmiriganj has 4 against the seed's 5.
  - Sylhet 106 (seed 104): Gowainghat 13 against 9, Golapganj 11 against 10, Dakshinsurma 8 against 10, Sylhet Sadar 7 against 8.
  - Sunamganj 88 (seed 87): Jamalganj 6 against 5; Dharmapasha 6 plus Madhyanagar 4 against the seed's 10 plus 0.
- **30 unions without a portal link:** mostly spelling variants the registry spells differently (e.g. বুলা/বুল্লা, দীঘলবাগ/দীঘলবাক, the four "… বানিয়াচং" names, সাচনা বাচার/সাচনাবাজার), the 4 Madhyanagar unions, and মধ্য জাফলং and বিছনাকন্দি. Links were not guessed.
- **Old pages:** population years printed: 2011 ×11, 2015 ×2, 2022, 2001; 107 give none. Prefer BBS 2022.
- **Raw texts:** `raw/*_glance.txt` have phone numbers and e-mails redacted. 37 এক নজরে pages that list people (members, mobiles) are used for figures only; their text is not saved (`raw` column in coverage.csv).

## Licence

No licence stated; facts only. Attribution: ইউনিয়ন পরিষদ পোর্টাল, সিলেট বিভাগ — জাতীয় তথ্য বাতায়ন (<union>.<district>.gov.bd). The national list is from the Bangladesh National Portal (bangladesh.gov.bd).
