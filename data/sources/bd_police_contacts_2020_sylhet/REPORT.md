# BD_POLICE_CONTACTS_2020_SYLHET — Police HQ contact list 2020, Sylhet Division

**Source:** police.gov.bd "Contacts of Bangladesh Police" workbook (XLSX uploaded 03-10-2020; trust level 4), sheets **SMP** and **Sylhet Range**, via `bd_police_contacts_2020/fetch.py --division sylhet`, accessed 2026-11-18. The rows of both sheets are kept as CSV in `raw/` (the 1.5 MB workbook is re-downloaded by fetch.py).

## Collected: 54 places
- **45 × `emergency.police_station`:**
  - 6 SMP thanas: Kotwali ("Kotoali Model"), Jalalabad, Airport, South Surma, Moglabazar, Shah Poran ("Shahporan"). `upazila_en` holds the SMP thana.
  - 39 district thanas: Sunamganj 12, Sylhet 11, Habiganj 9, Moulvibazar 7.
- **4 × `government.sp_office`:** one per district.
- **5 × `emergency`:** the SMP control room and hotline, and one control-room entry per district (control room and hotline numbers; Sylhet and Sunamganj also give a 2020 "Current Number").
- **Numbers:** phone = the official 01320-series "New Number". The 2020 "Current Number", the duty officer's number and official landlines are in `extra_json`. Designations only; no personal names.

## Data quality
- **Sheet layout:**
  - The district blocks are headed "Unit/Office Name : District Police Sylhet ." and "Districr Police Hobigonj / Moulvibazar / Sunamganj ." (sic).
  - OC posts are written "OC …", "OC, …", "OC. …", "Oc, …" and "OC.Sadar Thana".
  - The collector reads all of these, for this division only. "OC. DB" and "OC Watch" (Moulvibazar) are not thanas and are skipped.
- **E-mails:**
  - Not usable as printed: Chunarughat thana "occhunarughat.thana@gmail" (cut-off domain). The field is emptied and the cell kept in `extra_json.email_as_printed`.
  - Fixed: Bahubal thana "ocbahubalmodelthana @gmail.com" has a space before "@"; it is joined.
  - Thana mailboxes on gmail/yahoo, kept as published by Police HQ: Habiganj Sadar, Bahubal, Lakhai, Nabiganj, Ajmiriganj, Shayestaganj, Juri.
  - No e-mail is given for the other Moulvibazar or the Sunamganj thanas, or for the Moulvibazar SP.
- **Upazila:** set on all 39 district thanas, from the sheet spellings (Usmaninagar → Osmani Nagar, Biswanath → Bishwanath, Goainghat → Gowainghat, Companyganj → Companiganj, jaintapur → Jaintiapur, Madhobpur → Madhabpur, Lakhi → Lakhai, Ajmerigonj → Ajmiriganj, Saestagonj → Shayestaganj, Kamolgonj → Kamalganj, Chattak → Chhatak, Vishwambharpur → Bishwambarpur, Doarabazar → Dowarabazar, Dheri → Derai, Salla → Shalla, Maddhanagar → Madhyanagar, South Sunamjanj → South Sunamganj, Sadar → Habiganj / Sunamganj Sadar).
  - Sylhet Sadar and Dakshin Surma upazilas have no district thana here; they are policed by the SMP thanas.
- **Shared landline:** Lakhai and Bahubal OCs have the same official landline (08323-56011) as printed.
- **Moulvibazar SP:** its official landline cell is garbled in the sheet ('"522355427 *'); kept raw in `extra_json`.
- **Control-room names** use the district heading as printed (e.g. "Control Room, Districr Police Hobigonj").
- **Source spellings kept in `name_en`** (e.g. "Kotoali Model Thana", "kanaighat Thana", "Lakhi Thana", "Dheri Thana", "South Sunamjanj Thana").
- **Not collected:** the DIG Sylhet Range office and RRF Sylhet.
- **Numbers date from 2020;** the 2026 portals were not cross-checked by this collector.

## Licence
None stated → `null`.
