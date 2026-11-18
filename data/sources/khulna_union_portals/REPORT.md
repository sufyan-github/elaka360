# Union Parishad portals of Khulna Division

- **Collector:** `rajshahi_union_portals/fetch.py --division khulna`.
- **Union list:**
  - the DC portal lists with names: khulna, jashore, satkhira, meherpur, narail, chuadanga, magura, bagerhat, jhenaidah;
  - Kushtia (its DC page names no unions) is filled from the national portal's list of union portals (bangladesh.gov.bd/views/union-list), 66 unions;
  - Jhenaidah's Shailkupa is also from the national list: the DC list names 13, the national list 14.
  - In all, 80 rows come from the national list (noted per row). Total 582.
- **Portal links:**
  - from the DC lists;
  - else from the national list (325 links, `portal_link_from` in `raw/coverage.csv`);
  - else from the upazila portals' union pages.
- Each portal → menu item "এক নজরে" → label matcher (same as the other divisions).
- Per union, only robots.txt, the home page and the এক নজরে page are fetched. 8 parallel workers on different hosts, at least 1.2 s per host; 1,594 requests in about 3.5 minutes. Accessed 2026-11-18.

| Status | Unions |
|---|---|
| ok | 465 |
| no এক নজরে menu item | 83 |
| no portal link found | 23 |
| empty page | 11 |

| District | Unions | ok | From national list |
|---|---|---|---|
| Khulna | 68 | 54 | 0 |
| Jashore | 93 | 68 | 0 |
| Satkhira | 78 | 58 | 0 |
| Meherpur | 20 | 15 | 0 |
| Narail | 39 | 33 | 0 |
| Chuadanga | 40 | 33 | 0 |
| Magura | 36 | 32 | 0 |
| Bagerhat | 75 | 63 | 0 |
| Jhenaidah | 67 | 55 | 14 |
| Kushtia | 66 | 54 | 66 |

- **areas.csv (582):** one row per union.
  - `website` is filled only when the portal answered (559).
  - `source_url` is the এক নজরে page, or the list when there is none.
  - `notes` give the portal title. There is a DOUBT note where the title does not repeat the list's spelling (5: শেখহাটী/সেখহাটী, দিঘলিয়া "Digholiaup1", খাশিয়াল/খাসিয়াল, হাউলী/হাওলী, সিমলারোকনপুর/শিমলা-রোকনপুর).
- **facts.csv (854):**
  - villages 209, mouzas 188, population 169, area km² 145, households 85, wards 28;
  - area in other units: acres 11, unstated 9, sq miles 7, hectares 3;
  - 12 values flagged DOUBT.

## Caveats

- **582 rows vs 574 seed unions (registry 579):**
  - Meherpur's DC list has 20 (Sadar 7; registry and seed 5);
  - Satkhira has 78 (registry 77, seed 78);
  - Chuadanga has 40 (seed 35);
  - Jashore has 93 (seed 91);
  - Bagerhat's রাখালগাছি is listed by the DC, but its registry entry has no Bangla name, so no link was matched.
- **23 unions without a portal link:** spelling variants or unions the registry does not name the same way (e.g. বাাঁশদহ, দুর্বডাঙ্গা, শত্রুজিতপুর, হড়কা). Links were not guessed.
- **Jhenaidah Moheshpur:** "এস,বি,কে" is kept as printed (one union).
- **Old pages:** many এক নজরে pages are years old. Population years printed: 2011 ×13, 2001 ×2, single others (1973, 1983, 2007, 2010, 2014, 2022); most give none. Prefer BBS 2022.
- Raw page texts (`raw/*_glance.txt`, 465 files, about 3.5 MB) have phone numbers and e-mails redacted.

## Licence

No licence stated; facts only. Attribution: ইউনিয়ন পরিষদ পোর্টাল, খুলনা বিভাগ — জাতীয় তথ্য বাতায়ন (<union>.<district>.gov.bd). The national list is from the Bangladesh National Portal (bangladesh.gov.bd).
