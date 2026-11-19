# SYL_RANGE_POLICE_PORTALS_2026 — district police portals, Sylhet Range (excl. Sylhet District)

**Source (trust level 4, accessed 2026-11-18):** police.moulvibazar / police.habiganj / police.sunamganj `.gov.bd` and each upazila's thana portal police.<upazila>.<district>.gov.bd.

Sylhet Range is led by the Range DIG's office (policedig.sylhetdiv.gov.bd). Sylhet District is in SYLHET_POLICE_2026; SMP is in SYLHET_METRO_POLICE_THANAS_2026.

**fetch.py:** Sylhet tables and a new `main_sylhet()` on the Barishal pattern:
- SP officer card, with a fallback to `/pages/officers`;
- one thana portal per upazila;
- names composed from the upazila where the portal title is only "থানা";
- the Let's Encrypt intermediates are added for the run.

## Collected: 29 rows

| District | Rows | Thanas with phone |
|---|---|---|
| Sunamganj | 11 | 9 of 10 |
| Habiganj | 10 | 8 of 9 |
| Moulvibazar | 8 | 5 of 7 |

- **3 × `government.sp_office`:** all with landline + SP official mobile + `@police.gov.bd` e-mail (Moulvibazar 0241110376 / 01320119700; Habiganj 02996604520 / 01320118700; Sunamganj 02996600021 / 01320120700).
- **26 × `emergency.police_station`:** the OC's official mobile (01320-11xxxx / 12xxxx). Landlines only at Chunarughat and Lakhai. No thana e-mail.

## Contact rule
- Office landlines, police official mobiles, `*.gov.bd` e-mails only.
- No names, personal e-mails or other mobiles.

## Gaps and doubts
- **Not collected:**
  - police.shantiganj.sunamganj.gov.bd: self-signed TLS certificate, skipped;
  - police.madhyanagar.sunamganj.gov.bd: "Site is not available".
- **Composed names (15):** every Moulvibazar portal and most Habiganj portals are titled only "থানা", so the names come from the upazila (e.g. "মৌলভীবাজার সদর থানা"; the real name may include "মডেল").
- No phone at Barlekha, Sreemangal, Madhabpur, Dharmapasha.
- No thana count is collected. Cards are self-maintained and may be outdated.

## Licence
None stated → `null`.
