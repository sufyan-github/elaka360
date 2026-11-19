# District portals of the other five districts (Barishal Division)

- **Collector:** `division_district_portals/fetch.py --division barishal`.
- **Hosts:** jhalakathi, patuakhali, pirojpur, bhola and barguna `.gov.bd`.
  - Each is confirmed by its home-page title ("হোম | <জেলা> জেলা") and by the national office registry.
  - jhalokathi.gov.bd does not resolve; the registry and the divisional portal use jhalakathi.gov.bd.
- **Pages:** found from each menu. 21 pages, all fetched (`raw/pages.csv`, texts in `raw/`).
- **areas.csv (320):** 5 districts, 32 upazilas (all with website), 273 unions, 10 pourashavas.
- **facts.csv (74):** এক নজরে figures, stated counts and listed counts.

| District | Upazilas (stated) | Unions listed (stated) | Union links on list | From registry | Pourashavas named (stated) |
|---|---|---|---|---|---|
| Jhalokathi | 4 | 32 | 0 | 30 | 0 |
| Patuakhali | 8 (8) | 77 (77) | 75 | 2 | 5 (5) |
| Pirojpur | 7 (7) | 54 (53) | 0 | 42 | 0 (4) |
| Bhola | 7 (7) | 68 (70) | 68 | 0 | 5 (5) |
| Barguna | 6 | 42 | 41 | 0 | 0 |

## Layouts, gaps and conflicts

- **Jhalokathi:**
  - The page "উপজেলা ও ইউনিয়ন" (2026-09-29) prints "ঝালকাঠী সদর" and "কাঁঠালিয়া", kept as printed.
  - The upazila list menu item points to a non-page (`/pages/leaders`), so upazila websites were verified by
    fetching the portals.
  - এক নজরে is prose. Only the area (748.32 km²) is parsed. The two pourashavas it names ("ঝালকাঠি সদর ও নলছিটি")
    are not extracted.
  - Spellings not in the registry: নাথুল্লাবাদ, কুষঙ্গল.
- **Patuakhali:**
  - The union table uses "ঐ" (ditto) in the upazila column; the row takes the upazila of the row above.
  - The upazila and pourashava pages (2021-07-17) are prose with numbered items run together; they are split at the
    serials.
  - The pourashava list prints "X পৌরসভা, <উপজেলা>", so each parent is as printed.
  - Unions: 77 (registry 77, seed 72: Bauphal 15/14, Sadar 14/12, Dashmina 7/6, Rangabali 6/5).
  - The এক নজরে label "উপকৃত পরিবারের সংখ্যা" is not taken as a household count.
- **Pirojpur:**
  - There is no union list page. The menu item "উপজেলা তালিকা" (2026-08-03) prints each upazila as "X উপজেলা মোট
    ইউনিয়নঃ N টি" with numbered unions, and is used as the union list.
  - Zianagar lists 5 "(২ টি নব গঠিত)". The page prints "মোট ইউনিয়ন : ৫৩"; 54 rows are listed. Registry 53, seed 52.
  - Bhandaria lists ভান্ডারিয়া (7). The registry and the upazila portal have 6.
  - Many spellings differ from the registry, e.g. সিকদার/শিকদার মল্লিক, নাজিরপুর/নাজিরপুর সদর,
    কাউখালী/কাউখালি সদর. 12 unions have no website.
  - The "সকল ইউনিয়ন পরিষদের চেয়ারম্যান, মেম্বার ও সচিববৃন্দের তথ্য" file is not used.
- **Bhola:**
  - Upazila names are printed "ভোলা সদর, ভোলা।"; the ", ভোলা" is dropped and the printed text kept in notes.
  - Pourashavas come from menu links "পৌরসভা, ভোলা।" etc., with websites. "দৌলতখাঁন" is kept as printed.
  - The DC list has 68 unions: Charfesson 19 against the registry's 20, and the Lalmohan list prints "লডর্হার্ডিঞ্জ".
    এক নজরে says ৭০.
- **Barguna:**
  - The DC list links "বরগুনা সদর" union to sadar.barguna.gov.bd, the upazila portal. The link is not used; the
    registry names it বরগুনা (bargunaup).
  - Also listed: "… সদর" for আমতলী, বেতাগী, বামনা, পাথরঘাটা, বড়বগী.
  - এক নজরে is a PDF link; no figures.
  - The candidate page "ইউনিয়ন ভূমি অফিসসমূহ" was fetched but not used.
- **Pourashava parents:** as printed (Patuakhali) or inferred from same-named upazilas (Bhola).
- **Union websites:** where the list links them; otherwise from the national registry (noted per row). 15 unions
  have none.
- Raw page texts have phone numbers and e-mails redacted.

## Licence

No licence stated; facts only. Attribution: জেলা প্রশাসন, বরিশাল বিভাগ — জাতীয় তথ্য বাতায়ন (<district>.gov.bd).
