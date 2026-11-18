# BD_POLICE_CONTACTS_2020_CHATTOGRAM — Police HQ contact workbook (CMP and Chattogram Range)

**Source:** police.gov.bd "Contacts of Bangladesh Police" XLSX, uploaded 03-10-2020 (trust level 4). Accessed 2026-11-17 via `bd_police_contacts_2020/fetch.py --division chattogram`. Sheets used: CMP and Chattogram Range; `raw/` keeps their rows as CSV. Designations only, no personal names.

## Collected: 146 places
- **123 × `emergency.police_station`:**
  - 16 CMP thanas. `upazila_en` holds the CMP thana, with spellings as in `chattogram_metro_police` (e.g. Biazid Bostami → Bayezid Bostami, Port → Bandar, Akbor Shah → Akbarshah, Kornophuli → Karnaphuli).
  - 107 district thanas: Chattogram 16, Cumilla 18, Rangamati 11, Khagrachhari 9, Noakhali 9, Brahmanbaria 9, Cox's Bazar 8, Chandpur 8, Bandarban 7, Lakshmipur 6, Feni 6.
  - Phone = OC "New Number" (01320 series). The 2020 "Current Number", the official landline and the duty-officer number are in `extra_json` (duty officer on all 123). E-mail on 102.
- **11 × `government.sp_office`:** one per district (SP role number and e-mail).
- **12 × `emergency`:** the CMP control room (01320-057998, hotline 01320-057999) and 11 district control rooms with their hotlines.

## Mapping
- **Thana → upazila:**
  - Kotwali (Cumilla) → Cumilla Adarsha Sadar
  - Sadar South → Cumilla Sadar Dakshin
  - Kotwali (Rangamati) → Rangamati Sadar
  - Sodaram → Noakhali Sadar
  - Charjobbr → Subarnachar (Char Jabbar is Subarnachar's police station)
  - North Motlob / Motlob South → Matlab Uttar / Matlab Dakshin
  - Sadar → the district's Sadar upazila
  - Source spellings: Sitakondo, Sondip, Fotikchori, Raojan, Satkaniya, Lohagarh, Anawara, Chandnaish, Devidwar, Laksham, Baruda, Bagichhari, Jurachari, Vijayanagar, DaganBhuiyan, Ali kadam
- **Not upazilas (upazila_en empty, noted):** Jorargonj, Bojpur (Bhujpur), Chondroghona, Sajak (Sajek), Candroganj (Chandraganj), Bangra Bazar.

## Data quality
- **No "OC" prefix:** Brahmanbaria's and Chandpur's "Sadar Model Thana" rows; they are taken as the thana OC (noted).
- **Skipped:** "OC invest. Satkaniya Thana" (the investigation OC, not a separate thana).
- **SP designation:** Rangamati's SP is printed "Sp".
- **Shared values in the source:**
  - Chandgaon and Chawkbazar OCs share the e-mail occmp.cha@police.gov.bd.
  - North and South Matlab share the official and 2020 numbers and the e-mail.
- **E-mail fixes:** e-mails written with a space inside the domain ("police.gov. bd") are joined; trailing full stops are removed.
- **Missing:** Barkal thana is not in the sheet.
- **Not collected:** DIG Chattogram Range office and RRF Chattogram.
- **Numbers are from 2020.** The 2026 portals were not cross-checked by this collector.

## Licence
None stated → `null`.
