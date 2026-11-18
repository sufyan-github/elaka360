# Dhaka District portal (dhaka.gov.bd)

- **Collector:** `rajshahi_district_portal/fetch.py --division dhaka`. Host from the divisional portal's menu
  ("জেলা প্রশাসকের কার্যালয়, ঢাকা" → https://dhaka.gov.bd/), title "হোম | ঢাকা জেলা".
- **Pages** (from the menu): এক নজরে ঢাকা জেলা (updated 2026-11-10), উপজেলার তালিকা (2026-08-18),
  ইউনিয়ন (2026-08-27). Texts in `raw/`, list in `raw/pages.csv`.
- **areas.csv (71):** district, 5 upazilas, 62 unions, 3 pourashavas.
  - Upazilas Dhamrai, Dohar, Keraniganj, Nawabganj and Savar. Their websites are not linked from the list, so each
    `https://<sub>.dhaka.gov.bd/` was fetched and its title checked.
  - All 62 unions link their union portal. Names have "ইউনিয়ন" removed; the printed text is in `notes`.
  - The pourashavas দোহার, ধামরাই and সাভার are named only in the এক নজরে text ("৩টি। যথা: দোহার, ধামরাই ও
    সাভার পৌরসভা"). They have no website; each parent is inferred from the same-named upazila (noted).
- **facts.csv (17):**
  - area 1,463.60 km²;
  - population 14,734,701 (2022 census), printed in words "১ কোটি ৪৭ লক্ষ ৩৪ হাজার ৭০১ জন" and converted;
  - 5 upazilas, 3 pourashavas, 57 thanas, 2 city corporations, 86 unions (stated), 974 mouzas, 1,999 villages,
    4,035,241 households;
  - listed counts, and unions per upazila.

| Upazila | Unions |
|---|---|
| Savar | 12 |
| Dhamrai | 16 |
| Keraniganj | 12 |
| Nawabganj | 14 |
| Dohar | 8 |

## Gaps and conflicts

- **The city is not split into unions.** It is under the Dhaka North and South City Corporations ("২টি। যথা: ঢাকা
  উত্তর ও ঢাকা দক্ষিণ সিটি কর্পোরেশন"). No city-corporation rows here; see the city-corporation sources.
- **86 vs 62 unions:** the এক নজরে page says ৮৬টি, while the union list, the upazila portals and the national list of
  union portals all have 62. The 86 is recorded as printed; the page gives no date or reason for it.
- **Thanas:** 57 = 50 in the city-corporation area + 7 in the upazilas, as printed.
- **Upazila spelling:** the list prints কেরানীগঞ্জ; the divisional page prints কেরাণীগঞ্জ. Each row keeps its
  source's spelling.
- **Union name:** শোলস্না (Nawabganj) looks like a font-conversion artefact for শোল্লা (the upazila portal's
  spelling). Kept as printed.
- Union counts agree with the upazila portals and the national list for all 5 upazilas.

## Licence

No licence stated; facts only. Attribution: ঢাকা জেলা প্রশাসন, জাতীয় তথ্য বাতায়ন (dhaka.gov.bd).
