# Local Government Division (lgd.gov.bd) — Mymensingh Division

- Run: `python3 -I data/sources/lgd/fetch.py --division mymensingh` (accessed 2026-11-18). Key `LGD_2026_MYMENSINGH`, division `mymensingh`, kind `lgd`. No licence stated.
- Only the **"উপজেলা পরিষদের তালিকা"** page (updated 2023-05-31) has Mymensingh Division content. It prints **35 upazila names**: Sherpur 5, Mymensingh 13, Jamalpur 7, Netrokona 10. This equals the seed, HDX v03, DGHS and BBS 2022.
- All 35 Bangla names matched a seed upazila under the same district, including তারাকান্দা (Tarakanda), নকলা (Nokla), শ্রীবরদী (Sreebordi), বকশীগঞ্জ (Bokshiganj), দেওয়ানগঞ্জ (Dewangonj) and মোহনগঞ্জ (Mohongonj). `name_en` is the seed's English name, not LGD's.
- No hand check and no fetch.py change were needed; no warnings.
- Four names carry the suffix "উপজেলা" on the page: নালিতাবাড়ী, শ্রীবরদী, নকলা and ঝিনাইগাতী উপজেলা (Sherpur). `name_bn` keeps them as printed.
- `facts.csv` has 4 district `upazila_count` rows. The national union-parishad total (4,571) is not repeated here; it stays in the Rajshahi `LGD_2026` folder.
- There is no city-corporation, pourashava or union list, so this source says nothing about Mymensingh City Corporation.
  - The পৌরসভা, সিটি কর্পোরেশন, জেলা পরিষদ and উপজেলা পরিষদ menu pages still return HTTP 404 (`raw/menu_page_status.txt`).
  - The upazila-list page carries one attachment ("ফাইল ১", a .docx on objectstorage …/office-lgd/2024/12/3ed39e2b9f8e4de8baefac98a929c712.docx). fetch.py does not open it, and it was not opened for this run.
- Rerun check:
  - Rajshahi (no arguments) into a scratch folder: areas.csv, facts.csv and raw/ identical.
  - Rangpur/Dhaka/Chattogram/Khulna/Barishal/Sylhet: areas.csv and facts.csv identical. The Rangpur, Dhaka and Chattogram raw files differ only in their "ACCESSED" date line (2026-11-18 vs 2026-11-17).
  - The Chattogram run still prints its known warnings (মতলব unmapped, 103 of 104), as committed.
