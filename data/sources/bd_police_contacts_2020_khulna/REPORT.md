# BD_POLICE_CONTACTS_2020_KHULNA — Police HQ contact list 2020, Khulna Division

**Source:** police.gov.bd "Contacts of Bangladesh Police" workbook (XLSX uploaded 03-10-2020; trust level 4), sheets **KMP** and **Khulna Range**, via `bd_police_contacts_2020/fetch.py --division khulna`, accessed 2026-11-18. The rows of both sheets are kept as CSV in `raw/` (the 1.5 MB workbook is re-downloaded by fetch.py).

## Collected: 93 places
- **72 × `emergency.police_station`:**
  - 8 KMP thanas: Khulna (→ Khulna Sadar), Sonadanga, Labanchara, Harintana, Khalishpur, Daulatpur, Aranghata, Khan Jahan Ali. `upazila_en` holds the KMP thana.
  - 64 district thanas: Khulna 9, Bagerhat 9, Jashore 9, Satkhira 8, Kushtia 7, Jhenaidah 6, Chuadanga 5, Magura 4, Narail 4, Meherpur 3.
- **10 × `government.sp_office`:** one per district.
- **11 × `emergency`:** the KMP control room and hotline, and one control room per district.
- **Numbers:** phone = the official 01320-series "New Number". The 2020 "Current Number", the duty officer's number and official landlines are in `extra_json`. Designations only; no personal names.

## Data quality
- **Two "New Number" columns in the Khulna Range sheet.** The second (01320-140100 … 01320-150599) continues the national per-range series (Rangpur Range 0132013xxxx, Barishal Range 0132015xxxx) and is used. The first is kept as `*_new_number_first_column`. It conflicts with the second: SP Khulna's first-column 01320-149100 is SP Meherpur's second-column number, and Magura, Narail and Kushtia repeat the same control-room ranges. This choice is an inference; check against the 2026 district portals.
- **E-mails not usable as printed** (field emptied, cell kept in `extra_json.email_as_printed`): SP Satkhira "spsatkhira@.police. gov.bd", SP Narail "spnarail@police.gov.com".
- **Thana mailboxes:** 22 are gmail/yahoo addresses, kept as published by Police HQ.
- **Upazila set on 67 thanas.** Empty for Patkelghata, Benapol Port, Naragati ("Noragati"), EB (Islamic University) and Darsana: not upazilas.
- **Source spellings kept in `name_en`:** "Ovoynogor", "Jhikorgasa", "Shoilkupa", "Gagni", "Norail Sadar", "Morelgong" …
- **"OC DB" (KMP Detective Branch)** is not a thana and is left out. The range office and RRF Khulna are not collected.
- **Numbers date from 2020;** the 2026 portals were not cross-checked by this collector.

## Licence
None stated → `null`.
