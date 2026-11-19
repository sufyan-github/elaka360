# Rangpur District portal (rangpur.gov.bd)

- **Collector:** `rajshahi_district_portal/fetch.py --division rangpur`. Pages (from the menu): এক নজরে রংপুর জেলা
  (updated 2026-06-29), উপজেলা ও ইউনিয়ন (2026-06-18). Texts in `raw/`, list in `raw/pages.csv`.
- **areas.csv (88):** district, 8 upazilas, 76 unions, 3 pourashavas.
  - Upazila websites are not linked from the page; each `https://<sub>.rangpur.gov.bd/` was fetched and its title checked.
  - Unions are named without "ইউনিয়ন"; the printed text is kept in `notes`.
- **facts.csv (14):** area 2,400.56 km², population 3,169,615 (2022 census, printed "৩১,৬৯৬১৫"), 8 upazilas, 76 unions,
  3 pourashavas, unions per upazila.

| Upazila | Unions |
|---|---|
| Rangpur Sadar | 5 |
| Gangachara | 9 |
| Taragonj | 5 |
| Badargonj | 10 |
| Mithapukur | 17 |
| Pirgonj | 15 |
| Kaunia | 6 |
| Pirgacha | 9 |

## Gaps and conflicts

- **No union portal links** on the district page (union `website` empty); 34 of the 76 were found on upazila portals
  (see rangpur_union_portals).
- **Mithapukur:** "৬ নং কাফ্রিখাল" is printed twice; counted once (17). Same 17 on mithapukur.rangpur.gov.bd and the
  divisional list.
- **Pourashavas:** only named in the এক নজরে prose ("পৌরসভা -৩ (বদরগঞ্জ, হারাগাছ এবং পীরগঞ্জ)").
  - There is no pourashava list page and no website links.
  - The parents of বদরগঞ্জ and পীরগঞ্জ are inferred from the same-named upazila (noted).
  - হারাগাছ has no stated parent, so it is a district-level row.
- **Population:** male 1,568,608 + female 1,600,067 = 3,168,675, which is 940 short of the printed total (hijra not stated).
- **Area:** the geography page gives 2,367.84 km², while এক নজরে gives 2,400.56 ("উপজেলা ভিত্তিক অঞ্চল"). Both are recorded as printed, but only the
  এক নজরে figure is in facts.csv.
- Union counts agree with the divisional list and the upazila portals for all 8 upazilas.

## Licence

No licence stated; facts only. Attribution: রংপুর জেলা প্রশাসন, জাতীয় তথ্য বাতায়ন (rangpur.gov.bd).
