# Union Parishad portals of Dhaka Division

- **Collector:** `rajshahi_union_portals/fetch.py --division dhaka`.
- **Union list:** the 13 DC portal lists (738 named unions). Gopalganj (no list) and Faridpur (counts only) are filled
  from the national portal's list of union portals (bangladesh.gov.bd/views/union-list): 147 unions, noted per row.
  Total 885.
- **Portal links:**
  - from the DC lists;
  - else from the national list (220 links, `portal_link_from` in `raw/coverage.csv`);
  - else from the upazila portals' union pages.
- Each portal → menu item "এক নজরে" → label matcher (same as Rajshahi and Rangpur).
- Per union, only robots.txt, the home page and the এক নজরে page are fetched. 8 parallel workers on different hosts,
  ≥1.2 s per host; about 2,530 requests in 6 minutes.
- **Coverage (`raw/coverage.csv`):** 751 of 885 এক নজরে pages parsed.

| Status | Unions |
|---|---|
| ok | 751 |
| no এক নজরে menu item | 87 |
| empty page | 30 |
| no portal link found (Tangail 6, Munshiganj 7) | 13 |
| এক নজরে page HTTP 404 (ফুলসুতি, লস্করদিয়া, ঢেউখালী [Faridpur]; বেথুড়ী [Kashiani]) | 4 |

| District | Unions | ok |
|---|---|---|
| Narsingdi | 71 | 66 |
| Gazipur | 39 | 31 |
| Shariatpur | 65 | 53 |
| Narayanganj | 39 | 37 |
| Tangail | 120 | 92 |
| Kishoreganj | 108 | 99 |
| Manikganj | 65 | 60 |
| Dhaka | 62 | 47 |
| Munshiganj | 68 | 56 |
| Rajbari | 42 | 35 |
| Madaripur | 59 | 46 |
| Gopalganj | 67 | 63 |
| Faridpur | 80 | 66 |

- **areas.csv (885):** one row per union.
  - `website` is filled only when the portal answered (857).
  - `source_url` is the এক নজরে page, or the list when there is none.
  - `notes` give the portal title. Where the title does not repeat the list's spelling (39), there is a DOUBT note.
- **facts.csv (1,245):**
  - villages 281, population 259, mouzas 253, area km² 180, households 129, wards 49;
  - area in other units (sq miles 41, acres 29, hectares 1, unstated 23);
  - 16 values flagged DOUBT (implausible for a union).

## Caveats

- Faridpur has 80 here, not its stated 81: the national list's চাঁদপুর (Faridpur Sadar) has an English title only
  ("Chandpur Union") and no Bangla name, so it was left out.
- Many এক নজরে pages are years old (population years printed: 2011 ×19, 2001 ×11, 2022 ×7; most give none). Prefer
  BBS 2022 for population.
- Units vary (km², acres, sq miles, unstated) and are kept in `unit`.
- The 13 missing links were not guessed.
- Raw page texts (`raw/*_<district>_glance.txt`, 751 files, 4.8 MB) have phone numbers and e-mails redacted.

## Licence

No licence stated; facts only. Attribution: ইউনিয়ন পরিষদ পোর্টাল, ঢাকা বিভাগ — জাতীয় তথ্য বাতায়ন
(<union>.<district>.gov.bd). The national list is from the Bangladesh National Portal (bangladesh.gov.bd).
