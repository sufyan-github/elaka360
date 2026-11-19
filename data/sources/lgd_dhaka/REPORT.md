# Local Government Division (lgd.gov.bd) — Dhaka Division

- Run: `python3 -I data/sources/lgd/fetch.py --division dhaka` (accessed 2026-11-17). Key `LGD_2026_DHAKA`, division `dhaka`, kind `lgd`. No licence stated. No change to fetch.py was needed.
- Only the **"উপজেলা পরিষদের তালিকা"** page (updated 2023-05-31) has Dhaka Division content. It lists **89 upazilas**: Narsingdi 6, Gazipur 5, Shariatpur 6, Narayanganj 5, Tangail 12, Kishoreganj 13, Manikganj 7, Dhaka 5, Munshiganj 6, Rajbari 5, Madaripur 5 (including Dasar), Gopalganj 5, Faridpur 9. These are the same 89 as in the seed and HDX v03.
- All 89 Bangla names matched a seed upazila under the same district; `name_en` is the seed's English name, not LGD's.
  - Narsingdi's sadar upazila is printed as just "নরসিংদী" and is mapped to Narsingdi Sadar (noted in `notes`).
  - Narayanganj's names carry the suffix "উপজেলা" on the page (আড়াইহাজার উপজেলা, বন্দর উপজেলা, রূপগঞ্জ উপজেলা, সোনারগাঁ উপজেলা); `name_bn` keeps them as printed.
- `facts.csv` has 13 district `upazila_count` rows. The national union-parishad total (4,571) is not repeated here; it stays in the Rajshahi `LGD_2026` folder.
- There is no city-corporation, pourashava or union list, so this source says nothing about Dhaka North/South, Gazipur or Narayanganj City Corporation. The পৌরসভা, সিটি কর্পোরেশন, জেলা পরিষদ and উপজেলা পরিষদ menu pages still return HTTP 404 (`raw/menu_page_status.txt`), and no downloadable directory was found.
