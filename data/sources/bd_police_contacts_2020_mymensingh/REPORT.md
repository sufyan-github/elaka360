# BD_POLICE_CONTACTS_2020_MYMENSINGH — Police HQ contact list 2020, Mymensingh Division

**Source:** police.gov.bd "Contacts of Bangladesh Police" workbook (XLSX uploaded 03-10-2020; trust level 4), sheet **Mymenshing Range** (sic), via `bd_police_contacts_2020/fetch.py --division mymensingh`, accessed 2026-11-18. The rows of the sheet are kept as CSV in `raw/` (the 1.5 MB workbook is re-downloaded by fetch.py).

## Where the four districts sit
- **Sheet:** in 2020 Mymensingh, Jamalpur, Sherpur and Netrokona already had their own range sheet, "Mymenshing Range". It holds blocks "Range Office, Mymenshing" (DIG office; not collected) and "SP Office, Mymenshing / Netrokona / Jamalpur / Sherpur". They are not under Dhaka Range.
- **No metropolitan unit:** the workbook has no metropolitan sheet for Mymensingh. Its metro sheets are DMP, CMP, KMP, RMP, BMP, SMP, GMP and RRMP; Mymensingh city is policed by Kotwali PS of the district police.

## Collected: 44 places
- **36 × `emergency.police_station`:** Mymensingh 14, Netrokona 10, Jamalpur 7, Sherpur 5.
- **4 × `government.sp_office`:** one per district.
- **4 × `emergency`:** one control-room entry per district (control room and hotline numbers; Netrokona, Jamalpur and Sherpur also give a 2020 "Current Number").
- **Numbers:** phone = the official 01320-series "New Number". The 2020 "Current Number", the duty officer's number and official landlines are in `extra_json`. Designations only; no personal names.

## Data quality
- **Layout:** as in the Rajshahi Range sheet ("Inspector | OC Kotoali PS").
- **Duty officers:** only "Duty Officer" rows count as a thana's duty officer. Sherpur's "Duty Officer | (Wireless)" row is skipped; without that check it would have overwritten Jhenaigati's.
- **Upazila:** set on 35 thanas, from the sheet spellings (Kotoali → Mymensingh Sadar, Valuka → Bhaluka, Goforgong → Gafargaon, Gauripur → Gouripur, Ishwarganj → Iswarganj, Fulpur → Phulpur, Netrokona → Netrokona Sadar, Mohongong → Mohongonj, Jamalpur → Jamalpur Sadar, Melandha → Melandah, Matherganj → Madarganj, Dawanganj → Dewangonj, Bakshiganj → Bokshiganj, Sherpur → Sherpur Sadar).
  - Pagla PS lies in Gafargaon upazila; it is a thana, so `upazila_en` is empty.
- **E-mails:**
  - Mymensingh and Jamalpur thanas use police.gov.bd mailboxes. Netrokona and Sherpur thanas use gmail mailboxes named after the thana; kept as published by Police HQ.
  - Fixed: the trailing "-" in "oc.mohangonj@gmail.com-" and "oc.khaliajuri@gmail.com-".
  - Madan PS: the e-mail cell is a personal-looking gmail address. It is not used and is blanked in `raw/`, as in the DGHS extracts.
- **Official landlines:** kept raw in `extra_json`, including Sherpur's garbled cells (e.g. "932374008").
- **Control-room names** use the sheet heading (e.g. "Control Room, SP Office, Mymenshing"). Source spellings are kept in `name_en` (e.g. "Valuka PS", "Matherganj PS", "SP Office, Mymenshing").
- **Not collected:** the DIG Mymensingh Range office.
- **Numbers date from 2020;** the 2026 portals were not cross-checked by this collector.

## Licence
None stated → `null`.
