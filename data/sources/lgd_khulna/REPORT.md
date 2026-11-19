# Local Government Division (lgd.gov.bd) — Khulna Division

- Run: `python3 -I data/sources/lgd/fetch.py --division khulna` (accessed 2026-11-18). Key `LGD_2026_KHULNA`, division `khulna`, kind `lgd`. No licence stated. No change to fetch.py was needed (Khulna was already in its division table).
- Only the **"উপজেলা পরিষদের তালিকা"** page (updated 2023-05-31) has Khulna Division content. It prints **59 upazila names**: Jashore 8, Satkhira 7, Meherpur 3, Narail 3, Chuadanga 4, Kushtia 6, Magura 4, Khulna 9, Bagerhat 9, Jhenaidah 6. This equals the seed, HDX v03 and BBS 2022.
- All 59 Bangla names matched a seed upazila under the same district; `name_en` is the seed's English name, not LGD's. No warnings.
  - Seven Khulna-district names carry the suffix "উপজেলা" on the page: ফুলতলা, দিঘলিয়া, রূপসা, তেরখাদা, ডুমুরিয়া, দাকোপ and কয়রা. `name_bn` keeps them as printed.
- `facts.csv` has 10 district `upazila_count` rows. The national union-parishad total (4,571) is not repeated here; it stays in the Rajshahi `LGD_2026` folder.
- There is no city-corporation, pourashava or union list, so this source says nothing about Khulna City Corporation. The পৌরসভা, সিটি কর্পোরেশন, জেলা পরিষদ and উপজেলা পরিষদ menu pages still return HTTP 404 (`raw/menu_page_status.txt`), and no downloadable directory was found.
- Rerun check: `--division rajshahi|rangpur|dhaka|chattogram` into a scratch folder produced the same areas.csv and facts.csv. The Rajshahi raw/ files are identical; the others differ only in their "ACCESSED" date line.
