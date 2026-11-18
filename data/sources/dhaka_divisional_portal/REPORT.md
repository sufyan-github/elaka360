# Dhaka Divisional Commissioner portal (dhakadiv.gov.bd)

- **Collector:** `rajshahi_divisional_portal/fetch.py --division dhaka`. Host verified by its title "হোম | ঢাকা বিভাগ".
  Pages from the menu:
  - এক নজরে ঢাকা বিভাগ (updated 2026-05-21);
  - "জেলার তালিকা" (page title জেলা ও উপজেলা, 2026-05-21);
  - "ইউনিয়নের তালিকা", which links off-site to the national portal's list of union portals
    (bangladesh.gov.bd/views/union-list).
- "উপজেলার তালিকা" also links off-site (bangladesh.gov.bd/views/upazila-list). It was not fetched, because the
  district page already lists the upazilas.
- The national list is one 6 MB page with embedded JSON. Only the Dhaka Division part is kept:
  `raw/national_portal_list.csv` (89 upazila and 886 union portals with subdomain, title, the registry's geo name and
  BBS codes as given).
- **areas.csv (987):**
  - 13 districts (website = DC portal; these are linked from the portal menu);
  - 89 upazilas: names as printed on জেলা ও উপজেলা; website from the national list; no serial, so `code` is empty;
  - 885 unions from the national list. Website is the union portal; the name is the portal title without
    "ইউনিয়ন"; BBS codes are in `notes`.
- **facts.csv (99):**
  - division এক নজরে: 89 upazilas, 96 police thanas, 4 city corporations, 885 union parishads, 63 pourashavas,
    25,244 villages, 12,765 mouzas;
  - listed counts;
  - one `union_portal_count` per upazila.
- The এক নজরে page gives no area or population.

| District | Upazilas | Union portals listed |
|---|---|---|
| Narsingdi | 6 | 71 |
| Gazipur | 5 | 39 |
| Shariatpur | 6 | 65 |
| Narayanganj | 5 | 39 |
| Tangail | 12 | 120 |
| Kishoreganj | 13 | 108 |
| Manikganj | 7 | 65 |
| Dhaka | 5 | 62 |
| Munshiganj | 6 | 68 |
| Rajbari | 5 | 42 |
| Madaripur | 5 | 59 |
| Gopalganj | 5 | 67 |
| Faridpur | 9 | 80 |

## Conflicts and caveats

- **885 vs 886:** the national list has 886 Dhaka-division union portals. চাঁদপুর (chandpurup.faridpur.gov.bd, Faridpur
  Sadar) has only the English title "Chandpur Union" and no geo record, so it is not a row. That leaves 885, matching
  the এক নজরে count. faridpur.gov.bd states 12 unions for Faridpur Sadar; the list gives 11.
- **The national list is a portal registry, not an official union list.** Its BBS codes have errors, e.g. Rupganj and
  Bandar are both "68". Codes are therefore kept in `notes` only.
- **Per-upazila counts** agree with the DC lists and upazila portals everywhere except Boalmari: 10 here vs 11 on the
  upazila portal, which adds চাঁদপুর.
- **Upazila names on জেলা ও উপজেলা:**
  - নরসিংদী is printed without "সদর"; it is read as Narsingdi Sadar (noted);
  - কেরাণীগঞ্জ, মুন্সিগঞ্জ সদর, টুংগীপাড়া and ভুয়াপুর are kept as printed. The registry and DC portals print
    কেরানীগঞ্জ, মুন্সীগঞ্জ সদর, টুঙ্গিপাড়া and ভূঞাপুর.
- **Spelling:** 69 union names differ only in spelling from the DC lists. Kept as printed.
- The seed has about 876 unions; this source has 885 union portals. Some may be portals of unions that have since
  been absorbed (e.g. into Gazipur or Narayanganj city corporations); that is not stated on the page.

## Licence

No licence stated; facts only. Attribution: Office of the Divisional Commissioner, Dhaka (dhakadiv.gov.bd); the union
list is from the Bangladesh National Portal (bangladesh.gov.bd/views/union-list).
