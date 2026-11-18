# BAR_RANGE_POLICE_PORTALS_2026 — district police portals, Barishal Range (excl. Barishal District)

**Source (trust level 4, accessed 2026-11-18):**
- police.<district host> for Jhalokathi (police.jhalakathi.gov.bd), Patuakhali, Pirojpur, Bhola and Barguna;
- each upazila's thana portal police.<upazila>.<district host>.

Barishal Range is led by the Range DIG's office (policedig.barisaldiv.gov.bd). Barishal District is in BARISHAL_POLICE_2026; BMP is in BARISHAL_METRO_POLICE_THANAS_2026.

**fetch.py:** Barishal tables and a new `main_barishal()` on the Khulna pattern:
- SP officer card, with a fallback to `/pages/officers`;
- one thana portal per upazila;
- names composed from the upazila where the portal title is "থানা" or names the OC's office.

## Collected: 37 rows

| District | Rows | Thanas with phone / e-mail |
|---|---|---|
| Patuakhali | 9 | 6 / 2 of 8 |
| Pirojpur | 8 | 3 / 4 of 7 |
| Bhola | 8 | 3 / 3 of 7 |
| Barguna | 7 | 2 / 1 of 6 |
| Jhalokathi | 5 | 2 / 1 of 4 |

- 5 × `government.sp_office`, all with a phone (SP official mobile; Bhola and Barguna also a landline) and an `@police.gov.bd` e-mail.
- 32 × `emergency.police_station`; all 32 upazila thana portals answered.
- No facts.

## Contact rule
- **SP:** office landline, the SP's police official mobile, `*@police.gov.bd` e-mail.
- **Thanas:** office landline and the OC's police official mobile (01320-xxxxxx; the older 01713-37/38xxxx series on 3 rows); only `*.gov.bd` e-mails.
- No names, personal e-mails or other mobiles.

## Coverage and doubts
- Phone on 26 of 37 rows, e-mail on 16. No addresses or coordinates.
- **Composed names:** 10 names are composed from the upazila, where the portal title is "থানা" or "জিয়ানগর পুলিশ স্টেশন" (noted per row).
- Others are as titled, e.g. "আমতলী উপজেলা থানা", "দুমকী থানা".
- The Bhola SP portal's person-card link answers 404; the SP card came from the officer list.
- **Not covered:** thanas that are not upazilas (e.g. in Bhola or Kalapara) have no portal here, and no district published a thana count. Cards are self-maintained and may be outdated.

## Licence
None stated → `null`.
