# BD_POLICE_CONTACTS_2020_BARISHAL — Police HQ contact list 2020, Barishal Division

**Source:** police.gov.bd "Contacts of Bangladesh Police" workbook (XLSX uploaded 03-10-2020; trust level 4), sheets **BMP** and **Barisal Range**, via `bd_police_contacts_2020/fetch.py --division barishal`, accessed 2026-11-18. The rows of both sheets are kept as CSV in `raw/` (the 1.5 MB workbook is re-downloaded by fetch.py).

## Collected: 67 places
- **54 × `emergency.police_station`:**
  - 8 BMP thanas: Kotwali ("Kowtoali"), Kawnia ("Kaonia"), Airport, Bandar ("Port"), University, Kashipur, Charmonai ("Chormonai"), Rupatoli. `upazila_en` holds the BMP thana.
  - 46 district thanas: Barishal 10, Bhola 10, Patuakhali 9, Pirojpur 7, Barguna 6, Jhalokathi 4.
- **6 × `government.sp_office`:** one per district.
- **7 × `emergency`:** the BMP control room and hotline, and one control room or hotline per district. Jhalokathi, Bhola and Pirojpur list only a hotline.
- **Numbers:** phone = the official 01320-series "New Number". The 2020 "Current Number", the duty officer's number and official landlines are in `extra_json`. Designations only; no personal names.

## Data quality
- **BMP thanas that may not exist:** University, Kashipur, Charmonai and Rupatoli have only a "New Number" in the sheet (no landline, pre-2020 number or e-mail). Kotwali, Kawnia, Airport and Port have all of these. The four may have been planned thanas in 2020 (flagged on each row); check that they exist.
- **Posts written "Oc …":** the Barisal Range sheet writes most OC posts as "Oc …". The collector now reads both spellings, for this division only.
- **E-mails not usable as printed** (field emptied, cell kept in `extra_json.email_as_printed`):
  - Aguiljhara thana: "ocbar.ago@police.gov.b" (cut-off domain).
  - Borhanuddin thana: "ocborhanuddinps.gmail.com" (no "@").
- **E-mail fixed:** Kawkhali thana "ocpir.kow@police. gov.bd" has a space inside the domain; it is joined.
- **Thana mailboxes:** 9 are gmail addresses (Bhola District), kept as published by Police HQ. The Jhalokathi thana cells also list the "ops" mailbox; both are kept as printed.
- **Upazila set on 41 district thanas.** Empty for Kajirhat ("kajirhat", Barishal), Shashibhushan, South Aicha and Dularhat (Bhola) and Mohipur ("Muhipur", Patuakhali): not upazilas.
- **Numbers that break the sheet's own series** (kept as printed):
  - Shashibhushan OC: 01320-152333, while its investigation officer is 01320-152364.
  - Barishal District control room and hotline: 01320-162098/162099. Every other district's control numbers end its own 0132015xxxx block.
- **Source spellings kept in `name_en`:** "Bakergang", "Ujirpor", "Ghornadi", "Aguiljhara", "Moladi", "Hijla", "Mahendigang", "Jhalkhathi", "Nalciti", "Rajpur", "Bhula Model", "Dolotkhan", "Tojomoddin", "ChorFashion", "Baufol", "Dhosmina", "Mirajagang", "Nagirpur", "Mothbariya", "Vandariya", "Kawokhali", "Amtoli", "Pathorghata", "Bamona", "Taltoli" …
- **Indurkani:** the sheet already uses the name Indurkani (e-mail ocpir.zia@…).
- **Not collected:** the DIG range office and RRF Barisal.
- **Numbers date from 2020;** the 2026 portals were not cross-checked by this collector.

## Licence
None stated → `null`.
