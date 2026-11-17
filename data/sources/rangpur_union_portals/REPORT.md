# Union Parishad portals of Rangpur Division

- **Collector:** `rajshahi_union_portals/fetch.py --division rangpur`. Union list = the 8 DC portal lists (535
  unions). Portal links come from those lists; where missing, from the upazila portals' union pages (48 links).
- Each portal → menu item "এক নজরে" → label matcher (same as Rajshahi); printed label and value in `notes`.
- Per union: robots.txt, home page and the এক নজরে page only. 8 parallel workers on different hosts, ≥1.2 s per host.
- **Coverage (`raw/coverage.csv`):** 392 of 535 এক নজরে pages parsed.

| Status | Unions |
|---|---|
| ok | 392 |
| no portal link found (Rangpur 42, Panchagarh 23, Nilphamari 20) | 85 |
| no এক নজরে menu item | 50 |
| এক নজরে page HTTP 404 (কৈকুড়ী, টেপা খড়িবাড়ী, সোনারায় [Sundarganj], ভোগডাঙ্গা) | 4 |
| empty page (পাড়িয়া, আখানগর, চিলমারী, দাঁতভাঙ্গা) | 4 |

- **areas.csv (535):** one row per union from the DC lists.
  - `website` is filled only when the portal answered (445).
  - `source_url` is the এক নজরে page, or the district list when there is none.
  - `notes` give the portal title. Where the title does not repeat the list's spelling (19, mostly English titles or spelling variants such as ফরক্কাবাদ / ফরাক্কাবাদ), there is a DOUBT note.
  - ঘোগাদহ's portal answers "Site is not available", so it has no website.
- **facts.csv (874):** population 199, villages 167, mouzas 166, area km² 135, area in other units
  (acres/hectares/unstated) 75, households 105, wards 27. 10 values flagged DOUBT (implausible for a union).

## Caveats

- Many pages are years old and quote the 2011 census; prefer BBS 2022 for population.
- Units vary (km², acres, sq miles, unstated) and are kept in `unit`.
- The missing links (85) cannot be filled without guessing domains; they were not guessed.
- Raw page texts (`raw/*_glance.txt`, 380 files, 3.3 MB) have phone numbers and e-mails redacted.

## Licence

No licence stated; facts only. Attribution: ইউনিয়ন পরিষদ পোর্টাল, রংপুর বিভাগ — জাতীয় তথ্য বাতায়ন (<union>.<district>.gov.bd).
