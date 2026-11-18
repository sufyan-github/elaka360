# District portals of the other nine districts (Khulna Division)

- **Collector:** `division_district_portals/fetch.py --division khulna`.
- **Hosts:** jashore (alias jessore), satkhira, meherpur, narail, chuadanga, kushtia, magura, bagerhat and jhenaidah `.gov.bd`.
  - Each is confirmed by its home-page title ("হোম | <জেলা> জেলা") and by the national office registry.
  - The registry uses jashore.gov.bd. jessore.gov.bd serves the same site, and the Jashore portal links upazilas on jessore.gov.bd.
- **Pages:** found from each menu. 37 pages, all fetched (`raw/pages.csv`, texts in `raw/`, `raw/warnings.txt`).
- **areas.csv (528):** 9 districts, 50 upazilas (all with website), 447 unions, 22 pourashavas.
- **facts.csv (103):** এক নজরে figures, stated counts and listed counts.

| District | Upazilas | Unions listed (stated) | Union links | Pourashavas named (stated) |
|---|---|---|---|---|
| Jashore | 8 (8) | 93 (93) | 0 | 8 (8) |
| Satkhira | 7 | 78 (78) | 0 | 1 |
| Meherpur | 3 | 20 | 0 | 1 |
| Narail | 3 (3) | 39 (39) | 39 | 0 (3) |
| Chuadanga | 4 (4) | 40 (40) | 39 | 4 (4) |
| Kushtia | 6 | 0 | – | 4 |
| Magura | 4 (4) | 36 (36) | 8 | 1 (1) |
| Bagerhat | 9 | 75 | 0 | 3 |
| Jhenaidah | 6 (6) | 66 (67) | 0 | 0 |

## Layouts, gaps and conflicts

- **Jashore:** a table with rowspans, "বিভাগ | জেলা | উপজেলা | ইউনিয়ন"; the division column is skipped.
  - The heading "বাঘেরপাড়া" is matched as Bagherpara.
  - The pourashava list prints "বেনাপোলপৌরসভা, শার্শা" and "নওয়াপাড়া পৌরসভা, অভয়নগর". Rows are বেনাপোল পৌরসভা (Sharsha) and নওয়াপাড়া পৌরসভা (Abhaynagar), with the parent as printed and the printed text in notes.
  - Seed: 91 unions; registry and DC list: 93.
- **Satkhira:** the union cell runs numbered items together ("০১. ধানদিয়া০২. নগরঘাটা…"); they are split at the serials. The এক নজরে says ৭৮ (registry 77, seed 78). "বাাঁশদহ" is kept as printed.
- **Chuadanga:** each upazila is a paragraph heading ("চুয়াডাঙ্গা সদরঃ") above its own table. Two menu pages carry the same list. The DC list has 9 Sadar unions (seed 7, registry 9).
- **Kushtia:** the union page links six upazila pages and a PDF and names no unions. No union rows; union_portals uses the national list for Kushtia.
- **Magura:**
  - the heading "মহাম্মদপুর উপজেলা" is matched as Mohammadpur;
  - the pourashava page is prose with one numbered line, "১. জেলা পৌরসভা, মাগুরা।". This is read as মাগুরা পৌরসভা (Magura Sadar), noted on the row.
- **Bagerhat:** names are printed with English in brackets ("(১)কাড়াপাড়া (Karapara)"); the English is not used. The DC list has রাখালগাছি; the registry entry for it has no Bangla name.
- **Jhenaidah** (page dated 2021-06-17): comma lists per upazila.
  - "এস,বি,কে" (Moheshpur) is kept as one name.
  - Shailkupa prints "দিগনগর.কাচেঁরকোল" as one item, so 13 rows against 14 unions. Kept as printed; union_portals uses the national list for Shailkupa.
  - The list says ৬৭টি ইউনিয়ন.
- **Meherpur:** the DC list names 20 unions (Sadar 7). The registry and seed have 18 (Sadar 5).
- **Pourashava parents:** inferred from same-named upazilas (noted) unless printed. দর্শনা (Chuadanga) has no stated parent. চুয়াডাঙ্গা সদর পৌরসভা in এক নজরে is merged with the menu link চুয়াডাঙ্গা পৌরসভা.
- **Union websites:** only where the list links them (86). Union portal addresses are in khulna_union_portals.
- Raw page texts have phone numbers and e-mails redacted.

## Licence

No licence stated; facts only. Attribution: জেলা প্রশাসন, খুলনা বিভাগ — জাতীয় তথ্য বাতায়ন (<district>.gov.bd).
