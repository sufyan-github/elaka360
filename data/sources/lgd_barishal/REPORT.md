# Local Government Division (lgd.gov.bd) — Barishal Division

- Run: `python3 -I data/sources/lgd/fetch.py --division barishal` (accessed 2026-11-18). Key `LGD_2026_BARISHAL`, division `barishal`, kind `lgd`. No licence stated.
- Only the **"উপজেলা পরিষদের তালিকা"** page (updated 2023-05-31) has Barishal Division content. It prints **42 upazila names**: Jhalokathi 4, Patuakhali 8, Pirojpur 7, Barishal 10, Bhola 7, Barguna 6. This equals the seed, HDX v03, DGHS and BBS 2022.
- 41 Bangla names matched a seed upazila under the same district; `name_en` is the seed's English name, not LGD's.
  - One name needed a hand check: **ইন্দুরকানী** (Pirojpur) = seed Zianagar (জিয়ানগর), the upazila's former name.
  - Evidence: HDX's 2020 point for upazila 79-90 is named Zianagar, and the seed's three Zianagar unions are BBS 2022 Indurkani unions.
  - fetch.py change: `UPZ_SEED_BY_DIV` (used only for Barishal). The row's note says it was hand-checked.
  - No warnings remain.
  - One name carries the suffix "উপজেলা" on the page: বেতাগী উপজেলা. `name_bn` keeps it as printed.
- `facts.csv` has 6 district `upazila_count` rows. The national union-parishad total (4,571) is not repeated here; it stays in the Rajshahi `LGD_2026` folder.
- There is no city-corporation, pourashava or union list, so this source says nothing about Barishal City Corporation. The পৌরসভা, সিটি কর্পোরেশন, জেলা পরিষদ and উপজেলা পরিষদ menu pages still return HTTP 404 (`raw/menu_page_status.txt`), and no downloadable directory was found.
- Rerun check:
  - `--division rajshahi` (and no arguments) into a scratch folder: areas.csv, facts.csv and raw/ identical.
  - Rangpur/Dhaka/Chattogram/Khulna: areas.csv and facts.csv identical. The Rangpur, Dhaka and Chattogram raw files differ only in their "ACCESSED" date line (2026-11-18 vs 2026-11-17).
