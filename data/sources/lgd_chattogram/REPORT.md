# Local Government Division (lgd.gov.bd) — Chattogram Division

- Run: `python3 -I data/sources/lgd/fetch.py --division chattogram` (accessed 2026-11-17). Key `LGD_2026_CHATTOGRAM`, division `chattogram`, kind `lgd`. No licence stated. No change to fetch.py was needed (Chattogram was already in its division table).
- Only the **"উপজেলা পরিষদের তালিকা"** page (updated 2023-05-31) has Chattogram Division content. It prints **103 upazila names**: Cumilla 17, Feni 6, Brahmanbaria 9, Rangamati 10, Noakhali 9, Chandpur 8, Lakshmipur 5, Chattogram 15 (incl. Karnaphuli), Cox's Bazar 8, Khagrachhari 9 (incl. Guimara), Bandarban 7. The seed and HDX v03 have 104.
  - **Cox's Bazar:** the page lists 8 upazilas and has no Eidgaon (the seed, HDX v03 and BBS 2022 have 9). The `upazila_count` fact for Cox's Bazar is 8, as printed.
  - **Chandpur:** the page prints "মতলব" twice and does not say which is Matlab Uttar (North) and which is Matlab Dakshin (South). Both rows are kept as printed with `name_en` empty and a note. They are not assigned to a seed upazila.
- 101 of the 103 Bangla names matched a seed upazila under the same district; `name_en` is the seed's English name, not LGD's.
  - Noakhali's sadar upazila is printed as just "নোয়াখালী". It is mapped to Noakhali Sadar, with a note.
  - Five names carry the suffix "উপজেলা" on the page: ছাগলনাইয়া, সোনাগাজী and ফুলগাজী (Feni), সরাইল (Brahmanbaria), সীতাকুন্ড (Chattogram). `name_bn` keeps them as printed.
- `facts.csv` has 11 district `upazila_count` rows. The national union-parishad total (4,571) is not repeated here; it stays in the Rajshahi `LGD_2026` folder.
- The run printed 3 warnings: "unmapped upazila মতলব" twice, and "expected 104 upazilas, got 103". These are the gaps above.
- There is no city-corporation, pourashava or union list, so this source says nothing about Chattogram or Cumilla City Corporation. It also says nothing about the hill districts' own local-government bodies. The পৌরসভা, সিটি কর্পোরেশন, জেলা পরিষদ and উপজেলা পরিষদ menu pages still return HTTP 404 (`raw/menu_page_status.txt`), and no downloadable directory was found.
- Rerun check: `--division rajshahi|rangpur|dhaka` into a scratch folder produced the same areas.csv, facts.csv and raw/ files as the committed folders.
