# District portals of the other seven districts (Rangpur Division)

- **Collector:** `division_district_portals/fetch.py --division rangpur`.
- **Hosts:** panchagarh, dinajpur, lalmonirhat, nilphamari, gaibandha, thakurgaon and kurigram `.gov.bd`, each confirmed by fetching its home page (title "হোম | <জেলা> জেলা"). The divisional portal does not link the DC portals in its HTML (only the zila parishads).
- **Pages:** found from each menu: এক নজরে, উপজেলার তালিকা, ইউনিয়নের তালিকা / উপজেলা ও ইউনিয়ন, পৌরসভার তালিকা. 31 pages, all
  fetched (`raw/pages.csv`, page texts in `raw/`).
- **areas.csv (543):** 7 districts, 52 upazilas (all with a portal website), 459 unions, 25 pourashavas.
- **facts.csv (125):** এক নজরে figures, stated and listed counts.

| District | Upazilas | Unions (listed / stated) | Union portal links | Pourashavas named (stated) |
|---|---|---|---|---|
| Panchagarh | 5 | 43 / 43 | 7 | 0 (3) |
| Dinajpur | 13 | 103 / 103 | 103 | 9 (9) |
| Lalmonirhat | 5 | 45 / 45 | 45 | 2 (2) |
| Nilphamari | 6 | 60 / 60 | 40 | 4 (4) |
| Gaibandha | 7 | 81 / 81 | 80 | 4 (4) |
| Thakurgaon | 7 | 54 / 54 | 54 | 3 (—) |
| Kurigram | 9 | 73 / 73 | 73 | 3 (3) |

## Conflicts and caveats

- **Thakurgaon has 7 upazilas** (upazila and union lists, 2026-07-27).
  - The new রুহিয়া (6 unions) and ভূল্লী (5) were split from Thakurgaon Sadar, which now has 11.
  - Neither is in the project seed. Their English keys, Ruhia and Bhulli, come from the subdomains ruhia and bhulli.thakurgaon.gov.bd.
  - The divisional portal (2025-04) still shows 5 upazilas.
- **Facts not extracted:**
  - Thakurgaon's এক নজরে is prose only, so its area (1,809.52) and population (1,533,276) are not extracted.
  - Gaibandha's এক নজরে gives male, female and third gender on separate rows; its "মোট=২৫,৬২,২৩২" total is not extracted. It has no area figure.
- **Palashbari:** 8 unions here vs 9 on the divisional list (which adds পলাশবাড়ী).
- **Panchagarh:** says 3 pourashavas but names none. The upazila portals name পঞ্চগড়, দেবীগঞ্জ and বোদা পৌরসভা.
- **Bochaganj:** this list calls it বোচাগঞ্জ পৌরসভা; bochaganj.dinajpur.gov.bd calls it সেতাবগঞ্জ পৌরসভা.
- **Pourashava websites:** taken from the portals' menu links or the Dinajpur list's printed domains.
  - Sundarganj pourashava's menu link points to an upazila-portal page, so it has no website.
  - ঠাকুরগাঁও's link (amaderpaurashava.com, on the upazila portal) is not used here.
- **Pourashava parents** are inferred from the same-named upazila (noted on each row).

## Licence

No licence stated; facts only. Attribution: জেলা প্রশাসন, রংপুর বিভাগ — জাতীয় তথ্য বাতায়ন (<district>.gov.bd).
