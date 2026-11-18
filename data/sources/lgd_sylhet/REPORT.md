# Local Government Division (lgd.gov.bd) — Sylhet Division

- Run: `python3 -I data/sources/lgd/fetch.py --division sylhet` (accessed 2026-11-18). Key `LGD_2026_SYLHET`, division `sylhet`, kind `lgd`. No licence stated.
- Only the **"উপজেলা পরিষদের তালিকা"** page (updated 2023-05-31) has Sylhet Division content. It prints **41 upazila names**: Sylhet 13, Moulvibazar 7, Habiganj 9, Sunamganj 12. This equals the seed, HDX v03, DGHS and BBS 2022.
- 40 Bangla names matched a seed upazila under the same district; `name_en` is the seed's English name, not LGD's.
- Sunamganj: LGD prints দক্ষিণ সুনামগঞ্জ, which matches seed South Sunamganj directly. BBS 2022, HDX v03 and DGHS call the same upazila Shantiganj.
- One name needed a hand check: **ওসমানী** (Sylhet) = seed Osmaninagar (ওসমানী নগর).
  - LGD prints it without "নগর".
  - The other 12 Sylhet names on the page are the seed's other 12 Sylhet upazilas.
  - BBS 2022 (60-91-60), HDX v03 and DGHS list Osmaninagar in Sylhet district.
  - fetch.py change: `UPZ_SEED_BY_DIV["sylhet"]`. An entry may now carry its own reason; Barishal keeps "its former name", so its output is unchanged. The row's note says it was hand-checked.
- No warnings remain.
- One name carries the suffix "উপজেলা" on the page: মাধবপুর উপজেলা. `name_bn` keeps it as printed.
- `facts.csv` has 4 district `upazila_count` rows. The national union-parishad total (4,571) is not repeated here; it stays in the Rajshahi `LGD_2026` folder.
- There is no city-corporation, pourashava or union list, so this source says nothing about Sylhet City Corporation.
  - The পৌরসভা, সিটি কর্পোরেশন, জেলা পরিষদ and উপজেলা পরিষদ menu pages still return HTTP 404 (`raw/menu_page_status.txt`).
  - No downloadable directory was found.
- Rerun check:
  - Rajshahi (no arguments) into a scratch folder: areas.csv, facts.csv and raw/ identical.
  - Rangpur/Dhaka/Chattogram/Khulna/Barishal: areas.csv and facts.csv identical. The Rangpur, Dhaka and Chattogram raw files differ only in their "ACCESSED" date line (2026-11-18 vs 2026-11-17).
