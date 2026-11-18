# Khulna Divisional Commissioner portal (khulnadiv.gov.bd)

- **Collector:** `rajshahi_divisional_portal/fetch.py --division khulna`. Host verified by its title "হোম | খুলনা বিভাগ". Pages from the menu (`raw/pages.csv`, texts in `raw/`):
  - এক নজরে খুলনা বিভাগ (updated 2026-05-05);
  - জেলার তালিকা (2026-05-05);
  - খুলনা বিভাগের জেলা ও উপজেলা (2026-05-05).
- The menu item "ইউনিয়নের তালিকা" links the national portal's list of union portals (bangladesh.gov.bd/views/union-list), so its Khulna rows are used for unions. `raw/national_portal_list.csv` keeps the 59 upazila and 578 union rows.
- **areas.csv (647):**
  - 10 districts from "জেলার তালিকা". `code` is the list serial (`KHLDIV_LIST_SERIAL`). Website is the DC portal: not linked from this page, verified by title in the DC collectors.
  - 59 upazilas. The page prints one cell per district: a heading "<জেলা> জেলার উপজেলা সমূহ", then one "<নাম> উপজেলা" per line. Names are stored without "উপজেলা"; the printed text is in `notes`. No code: the row serial belongs to the district. Website is from the national registry.
  - 578 unions from the national list, with portal websites and the registry's BBS codes in `notes`.
- **facts.csv (62):** district count listed (10), upazila count listed (59), union portal count (578) and union portals per upazila.

| District | Upazilas listed | Union portals (national list) |
|---|---|---|
| Khulna | 9 | 68 |
| Bagerhat | 9 | 74 |
| Satkhira | 7 | 77 |
| Jashore | 8 | 93 |
| Narail | 3 | 39 |
| Magura | 4 | 36 |
| Jhenaidah | 6 | 67 |
| Kushtia | 6 | 66 |
| Chuadanga | 4 | 40 |
| Meherpur | 3 | 18 |

## Conflicts and caveats

- **578 vs 579 union portals:** the registry has 579 Khulna union portals. One, rakhalgachiup.bagerhat.gov.bd, has only the English title "Rakhalgachi Union" and no Bangla geo name, so it was left out (`raw/warnings.txt`). The seed has 574 unions.
- **এক নজরে is prose:** the label matcher found no figures, so there are no division facts from it. The page says "৫৯ টি উপজেলা ও ১০টি জেলা", area ২২,২৮৫ km² and population ১৫,৫৬৩,০০০ (2011 census, as quoted). It also has a per-district table (area; population 1991, 2001, 2011, 2022). These were not extracted; they are in `raw/glance.txt`. The table's total row prints "১২,৬৮৮,৩৮৩২" for 1991, which is a misprint.
- **Spellings kept as printed:** মনিরামপুর (seed মণিরামপুর), মোহাম্মদপুর (seed মহম্মদপুর), কালীগঞ্জ for Satkhira's upazila (seed কালিগঞ্জ).
- **Registry addresses:** Jashore portals are on jashore.gov.bd (the seed has jessore.gov.bd; both serve the same site). Kushtia's Mirpur is mirpur.kushtia.gov.bd; the seed's mirpurkushtia answers "Site is not available". Khulna's Dakop is dacope.khulna.gov.bd; dakop.khulna.gov.bd serves the same portal.

## Licence

No licence stated; facts only. Attribution: Office of the Divisional Commissioner, Khulna (khulnadiv.gov.bd); union and upazila portal list from the Bangladesh National Portal (bangladesh.gov.bd/views/union-list).
