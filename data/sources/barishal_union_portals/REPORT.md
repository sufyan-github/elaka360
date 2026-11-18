# Union Parishad portals of Barishal Division

- **Collector:** `rajshahi_union_portals/fetch.py --division barishal`.
- **Union list:**
  - the DC portal lists for all six districts (Pirojpur's is its "উপজেলা তালিকা" page);
  - Bhola's Charfesson comes from the national portal's list of union portals (bangladesh.gov.bd/views/union-list):
    the DC list names 19, the national list 20.
  - Total 362.
- **Portal links:**
  - from the DC lists;
  - else from the national list (151, `portal_link_from` in `raw/coverage.csv`);
  - else from the upazila portals' union pages.
- Each portal → menu item "এক নজরে" → label matcher.
- Only robots.txt, the home page and the এক নজরে page are fetched per union. 8 parallel workers on different hosts,
  at least 1.2 s per host. 919 requests in about 2 minutes. Accessed 2026-11-18.

| Status | Unions |
|---|---|
| ok | 243 |
| no এক নজরে menu item | 87 |
| no portal link found | 26 |
| empty page | 4 |
| page error (HTTP 404, লতাচাপলী) | 1 |
| portal error (TLS, m.baliataliup.barguna.gov.bd) | 1 |

| District | Unions | ok | From national list |
|---|---|---|---|
| Barishal | 88 | 58 | 0 |
| Jhalokathi | 32 | 21 | 0 |
| Patuakhali | 77 | 62 | 0 |
| Pirojpur | 54 | 22 | 0 |
| Bhola | 69 | 57 | 20 |
| Barguna | 42 | 23 | 0 |

- **areas.csv (362):** one row per union.
  - `website` only when the portal answered (334).
  - `source_url` is the এক নজরে page, or the list when there is none.
  - DOUBT where the portal title does not repeat the list's spelling (মগড়/মগর, লডর্হার্ডিঞ্জ/লর্ড হার্ডিঞ্জ).
- **facts.csv (324):**
  - mouzas 72, villages 71, population 58, area km² 55, households 38, wards 13;
  - area in other units: acres 7, sq miles 5, unstated 4, hectares 1;
  - 5 values flagged DOUBT.

## Caveats

- **362 rows vs 348 seed unions (registry 361):** Patuakhali 77 (seed 72), Barishal 88 (seed 85), Bhola 69 (seed 64),
  Pirojpur 54 (seed 52), Barguna 42 (seed 43).
- **26 unions without a portal link:** spelling variants the registry spells differently, e.g. শায়েস্তাবাদ/সায়েস্তাবাদ,
  সিকদার/শিকদার মল্লিক, নাজিরপুর/নাজিরপুর সদর. Also বরগুনা সদর: the DC links the upazila portal, not used; the registry
  names it বরগুনা. Links were not guessed.
- **Old pages:** population years printed: 2011 ×7, 2001 ×2, 2012, 2017; most give none. Prefer BBS 2022. Words like
  "১৪ হাজার ১৩৯ জন" are not converted (flagged DOUBT).
- **Raw texts:** `raw/*_glance.txt` have phone numbers and e-mails redacted. 37 এক নজরে pages that also list people
  (members, mobiles) are used for figures only; their text is not saved (`raw` column in coverage.csv).

## Licence

No licence stated; facts only. Attribution: ইউনিয়ন পরিষদ পোর্টাল, বরিশাল বিভাগ — জাতীয় তথ্য বাতায়ন (<union>.<district>.gov.bd). The national list is from the Bangladesh National Portal (bangladesh.gov.bd).
