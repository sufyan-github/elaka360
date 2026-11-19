# Local Government Division (lgd.gov.bd) — Rangpur Division

- Run: `python3 -I data/sources/lgd/fetch.py --division rangpur` (accessed 2026-11-17). Key `LGD_2026_RANGPUR`, division `rangpur`, kind `lgd`. No licence stated.
- Only the **"উপজেলা পরিষদের তালিকা"** page (updated 2023-05-31) has Rangpur Division content. It lists **58 upazilas**: Panchagarh 5, Dinajpur 13, Lalmonirhat 5, Nilphamari 6, Gaibandha 7, Thakurgaon 5, Rangpur 8, Kurigram 9. These are the same 58 as in the seed and HDX.
- All 58 Bangla names matched a seed upazila under the same district, and `name_en` is the seed's English name, not LGD's.
  - Panchagarh's sadar upazila is printed as just "পঞ্চগড়" and is mapped to Panchagarh Sadar (noted in `notes`).
  - Some names carry the suffix "উপজেলা" on the page; `name_bn` keeps them as printed.
- `facts.csv` has 8 district `upazila_count` rows. The national union-parishad total (4,571) is not repeated here; it stays in the Rajshahi `LGD_2026` folder.
- There is no union, pourashava or city-corporation list. The পৌরসভা, সিটি কর্পোরেশন, জেলা পরিষদ and উপজেলা পরিষদ menu pages still return HTTP 404 (`raw/menu_page_status.txt`), and no downloadable directory was found.
