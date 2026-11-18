# Khulna District portal (khulna.gov.bd)

- **Collector:** `rajshahi_district_portal/fetch.py --division khulna`.
- **Host:** khulna.gov.bd, title "হোম | খুলনা জেলা"; the national registry lists its upazila portals under khulna.gov.bd.
- **Pages** (`raw/pages.csv`, texts in `raw/`):
  - এক নজরে জেলার পরিচিতি (updated 2026-10-08);
  - উপজেলা পরিষদের তালিকা (2026-10-08);
  - ইউনিয়ন পরিষদসমূহের তালিকা (2026-10-08);
  - পৌরসভার তালিকা (2026-10-14).
- **areas.csv (80):** district, 9 upazilas, 68 unions and 2 pourashavas.
  - Every upazila and union has a website, linked from the lists. The upazila list links dakop.khulna.gov.bd; the registry uses dacope.khulna.gov.bd, and both serve the same portal.
  - The union page prints each upazila as a heading above its own table, with one union per line ("১।আইচগাতি"). The list serial is not a union number, so `code` is empty.
- **facts.csv (12):** upazila count listed (9), unions per upazila, union count listed (68), pourashava count listed (2).

| Upazila | Unions | Upazila | Unions |
|---|---|---|---|
| Rupsha | 5 | Botiaghata | 7 |
| Terokhada | 6 | Dakop | 9 |
| Digholia | 6 | Paikgasa | 10 |
| Fultola | 4 | Koyra | 7 |
| Dumuria | 14 | | |

## Gaps and conflicts

- **No figures in এক নজরে:** the page is prose (history, naming). There are no area, population or count facts; prefer BBS 2022.
- **Pourashavas:** the list names only চালনা and পাইকগাছা. চালনা has its website (pourashava.dakop.khulna.gov.bd) but no stated parent, so `upazila_en` is empty. পাইকগাছা's parent is inferred from the same-named upazila.
- **The city** is under Khulna City Corporation; there are no city-corporation rows here.
- 68 unions agree with the national registry (68) and the seed (68).

## Licence

No licence stated; facts only. Attribution: খুলনা জেলা প্রশাসন, জাতীয় তথ্য বাতায়ন (khulna.gov.bd).
