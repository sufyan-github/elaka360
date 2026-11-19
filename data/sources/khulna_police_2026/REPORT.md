# KHULNA_POLICE_2026 — Khulna District Police

**Source (trust level 4, accessed 2026-11-18):**
- police.khulna.gov.bd: SP officer card;
- the 9 upazila thana portals police.<upazila>.khulna.gov.bd: office landline, OC's police official mobile and e-mail.

Khulna city is policed by KMP (KHULNA_METRO_POLICE_THANAS_2026).

**fetch.py:**
- New `main_khulna()` (Rangpur/Dhaka pattern).
- `KP_POLICE_SUB` maps Dacope to police.dacope.khulna.gov.bd: police.dakop.khulna.gov.bd fails the TLS handshake, and the dacope host is titled "দাকোপ থানা, খুলনা".

## Collected (10 rows)
- 1 × `government.sp_office`: পুলিশ সুপারের কার্যালয়, খুলনা — 041725377, SP official mobile 01320140100, spkhulna@police.gov.bd; fax 041725229 in `extra_json`.
- 9 × `emergency.police_station`: Batiaghata, Dacope, Dumuria, Dighalia, Koyra, Paikgachha, Phultala, Rupsa (portal spells it "রুপসা থানা"), Terokhada.
  - Phone on 5 of 9 (OC official mobile and/or landline): Batiaghata, Dacope, Dumuria, Paikgachha, Rupsa.
  - No thana e-mail.
  - Terokhada's portal title is the bare host; its name is composed from the upazila.
- **facts:** none.

## Gaps and doubts
- police.khulna.gov.bd publishes no thana list, thana count or contact table. Its "এক নজরে" only describes the office building, and "ডাক যোগাযোগ" has no street address, so the SP row has no address.
- Dighalia, Koyra, Phultala and Terokhada portals have no officer-in-charge card with a number.
- khulnadistrict.police.gov.bd did not respond.
- Thanas that are not upazilas are not covered.
- Officers' names, personal e-mails and other mobiles are not copied.

## Licence
None stated → `null`.
