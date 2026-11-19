# CTG_RANGE_POLICE_PORTALS_2026 — district police portals, Chattogram Range (excl. Chattogram District)

**Source (trust level 4, accessed 2026-11-18):**
- police.<district>.gov.bd for Cumilla (police.comilla), Feni, Brahmanbaria, Rangamati, Noakhali, Chandpur, Lakshmipur, Cox's Bazar (police.coxsbazar), Khagrachhari and Bandarban;
- each upazila's thana portal police.<upazila>.<district host>.

Chattogram Range is led by the Range DIG's office (dig.chittagongdiv.gov.bd, which publishes no district or thana list). Chattogram District is in CHATTOGRAM_POLICE_2026; CMP is in CHATTOGRAM_METRO_POLICE_THANAS_2026.

**fetch.py:**
- New `main_chattogram()` on the Dhaka pattern: SP officer card plus one portal per upazila thana.
- `sp_office_row()` takes an optional `host` (default unchanged).
- Titles "বাংলাদেশ পুলিশ X থানা" are trimmed; "মডেল থানা, X" becomes "<upazila> মডেল থানা".

| District | Rows | Thanas with phone / e-mail |
|---|---|---|
| Cumilla | 18 | 14 / 1 of 17 |
| Rangamati | 11 | 6 / 3 of 10 |
| Brahmanbaria | 10 | 9 / 1 of 9 |
| Noakhali | 10 | 9 / 4 of 9 |
| Khagrachhari | 10 | 6 / 0 of 9 |
| Chandpur | 9 | 8 / 0 of 8 |
| Cox's Bazar | 9 | 7 / 0 of 8 |
| Bandarban | 8 | 1 / 2 of 7 |
| Feni | 7 | 4 / 2 of 6 |
| Lakshmipur | 6 | 3 / 0 of 5 |

Categories: 88 `emergency.police_station`, 10 `government.sp_office` (all 10 with phone and `@police.gov.bd` e-mail). No facts.

## Contact rule
SP: office landline, the SP's police official mobile and the `*@police.gov.bd` e-mail. Thanas: office landline and the OC's police official mobile (01320-xxxxxx, or the older 01713-37/38xxxx series on 3 rows); only `*.gov.bd` e-mails. No names, personal e-mails or other mobiles.

## Coverage and doubts
- **Coverage:** phone on 77 of 98 rows, e-mail on 23; no addresses or coordinates.
- **Names composed** from the upazila where the portal title is a bare "থানা" or "মডেল থানা, X" (41 rows, noted per row). Cumilla's Sadar thanas are named from the upazila ("আদর্শ সদর থানা", "সদর দক্ষিণ থানা"), not Kotwali Model thana.
- **Not covered:**
  - police.eidgaon.coxsbazar.gov.bd failed TLS verification (self-signed certificate).
  - Thanas that are not upazilas have no portal here.
  - No district published a thana count.
- Cards are self-maintained and may be outdated.

## Licence
None stated → `null`.
