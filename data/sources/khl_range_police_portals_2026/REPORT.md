# KHL_RANGE_POLICE_PORTALS_2026 — district police portals, Khulna Range (excl. Khulna District)

**Source (trust level 4, accessed 2026-11-18):**
- police.<district host> for Jashore (police.jessore.gov.bd; police.jashore.gov.bd serves the same site), Satkhira, Meherpur, Narail, Chuadanga, Kushtia, Magura, Bagerhat and Jhenaidah;
- each upazila's thana portal police.<upazila>.<district host>.

Khulna Range is led by the Range DIG's office (policedig.khulnadiv.gov.bd, which publishes no district or thana list). Khulna District is in KHULNA_POLICE_2026; KMP is in KHULNA_METRO_POLICE_THANAS_2026.

**fetch.py:**
- Khulna tables.
- New `main_khulna()` on the Chattogram pattern: SP officer card plus one portal per upazila thana.
- If the home page's person card links another officer (Meherpur: an Additional SP), the SP card is taken from `/pages/officers`.
- Titles naming the OC's office ("থানা ভারপ্রাপ্ত কর্মকর্তার কার্যালয়", "থানা অফিসার ইনচার্জ এর কার্যালয়, দৌলতপুর, কুষ্টিয়া") become "<upazila> থানা".

## Collected: 59 rows

| District | Rows | Thanas with phone / e-mail |
|---|---|---|
| Bagerhat | 10 | 6 / 0 of 9 |
| Jashore | 9 | 7 / 0 of 8 |
| Satkhira | 8 | 4 / 0 of 7 |
| Jhenaidah | 7 | 5 / 3 of 6 |
| Kushtia | 7 | 6 / 1 of 6 |
| Chuadanga | 5 | 2 / 3 of 4 |
| Magura | 5 | 4 / 2 of 4 |
| Meherpur | 4 | 1 / 0 of 3 |
| Narail | 4 | 2 / 0 of 3 |

Categories: 50 `emergency.police_station` (all 50 upazila thana portals answered), 9 `government.sp_office` (all with phone and `@police.gov.bd` e-mail). No facts.

## Contact rule
- SP: office landline, the SP's police official mobile and the `*@police.gov.bd` e-mail.
- Thanas: office landline and the OC's police official mobile (01320-xxxxxx; the older 01713-37/38xxxx series on 1 row); only `*.gov.bd` e-mails.
- No names, personal e-mails or other mobiles.

## Coverage and doubts
- **Coverage:** phone on 46 of 59 rows, e-mail on 18; no addresses or coordinates.
- **Composed names:** 23 names are composed from the upazila, where the portal title is the bare host ("police.abhaynagar.jessore"), "থানা" or the OC's office (noted per row). Other names are as titled, e.g. "মেহেরপুর থানা" (Meherpur Sadar), "জীবন নগর থানা", "কুষ্টিয়া মডেল থানা".
- **Not covered:** thanas that are not upazilas have no portal here; no district published a thana count.
- Cards are self-maintained and may be outdated.

## Licence
None stated → `null`.
