# Union Parishad portals of Chattogram Division

- **Collector:** `rajshahi_union_portals/fetch.py --division chattogram`.
- **Union list:**
  - the 10 DC portal lists with names (chattogram, comilla, feni, brahmanbaria, rangamati, chandpur, lakshmipur, coxsbazar, khagrachhari, bandarban);
  - Noakhali (its list is a PDF) is filled from the national portal's list of union portals (bangladesh.gov.bd/views/union-list), 89 unions.
  - Where a DC list names fewer unions in the district than the national list, each short upazila is taken from the national list instead. This applies to Brahmanbaria (Sadar 10 → 11, Sarail 8 → 9) and Cox's Bazar (Moheshkhali 5 → 8, Pekua 2 → 7, Eidgaon 4 → 5).
  - The 3 Moheshkhali unions printed under Kutubdia were dropped (logged in `raw/warnings.txt`).
  - In all, 129 rows come from the national list (noted per row). Total 959.
- **Portal links:**
  - from the DC lists;
  - else from the national list (389 links, `portal_link_from` in `raw/coverage.csv`);
  - else from the upazila portals' union pages.
- Each portal → menu item "এক নজরে" → label matcher (same as the other divisions).
- Per union, only robots.txt, the home page and the এক নজরে page are fetched. 8 parallel workers on different hosts, at least 1.2 s per host; 2,567 requests in about 6 minutes. Accessed 2026-11-17/18 (the run passed midnight).

| Status | Unions |
|---|---|
| ok | 758 |
| no এক নজরে menu item | 128 |
| no portal link found | 58 |
| empty page | 11 |
| HTTP 404 (পদুয়া ×2, বৈলতলী, ঘুমধুম) | 4 |

| District | Unions | ok | From national list |
|---|---|---|---|
| Cumilla | 198 | 150 | 0 |
| Feni | 43 | 35 | 0 |
| Brahmanbaria | 100 | 72 | 20 |
| Rangamati | 50 | 43 | 0 |
| Chandpur | 88 | 78 | 0 |
| Lakshmipur | 58 | 42 | 0 |
| Chattogram | 190 | 160 | 0 |
| Cox's Bazar | 71 | 59 | 20 |
| Khagrachhari | 38 | 33 | 0 |
| Bandarban | 34 | 17 | 0 |
| Noakhali | 89 | 69 | 89 |

- **areas.csv (959):** one row per union.
  - `website` is filled only when the portal answered (890).
  - `source_url` is the এক নজরে page, or the list when there is none.
  - `notes` give the portal title. There is a DOUBT note where the title does not repeat the list's spelling (43), or where the national list has the union in another upazila (19).
- **facts.csv (1,255):**
  - population 282, villages 270, mouzas 247, area km² 193, households 109, wards 56;
  - area in other units: acres 40, unstated 27, sq miles 24, hectares 7;
  - 23 values flagged DOUBT.

## Caveats

- **959 rows vs about 950 unions (seed 950; registry 953):**
  - Cumilla's DC list prints Lalmai's 8 unions also under Sadar South, and চান্দলা under both Barura and Brahmanpara. Kept as printed with DOUBT notes; those rows have no portal link;
  - Cumilla is 198 vs its stated ১৯৩;
  - same-named unions in one district (e.g. পদুয়া in Rangunia and Lohagara, ধর্মপুর in Fatikchhari and Satkania) are real, separate unions.
- **Lakshmipur:** Chandraganj's 9 unions (as the DC lists them) have no portal link: the registry still parents their portals to Lakshmipur Sadar.
- **Spelling:** names not matched to a registry portal include spelling variants and font-conversion artefacts (Brahmanbaria বুধমত্মী, রছুলস্নাবাদ, কু-া). The 58 missing links were not guessed.
- **Old pages:** many এক নজরে pages are years old. Population years printed: 2011 ×29, 2022 ×7, 2001 ×6, others single; most give none. Prefer BBS 2022.
- Raw page texts (`raw/*_glance.txt`, 758 files, about 6 MB) have phone numbers and e-mails redacted.

## Licence

No licence stated; facts only. Attribution: ইউনিয়ন পরিষদ পোর্টাল, চট্টগ্রাম বিভাগ — জাতীয় তথ্য বাতায়ন (<union>.<district>.gov.bd). The national list is from the Bangladesh National Portal (bangladesh.gov.bd).
