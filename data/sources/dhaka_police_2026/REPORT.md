# DHAKA_POLICE_2026 — Dhaka District Police

**Source (trust level 4, accessed 2026-11-17):** police.dhaka.gov.bd (Superintendent's officer card, "যোগাযোগ" page), the thana portals police.<upazila>.dhaka.gov.bd, and the Dhaka DC portal's "এক নজরে ঢাকা জেলা" for the thana count. Dhaka city is policed by DMP (DHAKA_METRO_POLICE_THANAS_2026).

**fetch.py:** new `main_dhaka()` (SP card + contact-page address, DC glance fact, the 5 upazila thana portals). The shared thana-portal helpers now also read titles such as "উপজেলা থানা, X", "বাংলাদেশ পুলিশ, X থানা" and a bare "থানা", and skip "Site is not available" placeholders (Rajshahi code path unchanged).

## Collected (6 rows)
- 1 × `government.sp_office`: পুলিশ সুপারের কার্যালয়, ঢাকা — 0241051062, SP official mobile 01320089300, spdhaka@police.gov.bd, fax in `extra_json`; address "১৬, জনসন রোড" and an older office number (02-7112774) from "যোগাযোগ".
- 5 × `emergency.police_station`: Dohar (OC official mobile), Nawabganj (landline + OC mobile), Dhamrai, Keraniganj, Savar.
- facts: 7 thanas in the upazila area (DC portal: "মোট ৫৭টি (৫০টি সিটি কর্পোরেশন এলাকায়, ৭টি উপজেলা এলাকায়)").

## Coverage and gaps
- **Coverage:** phone on 3 of 6, e-mail on 1 (the SP); no coordinates.
- **Placeholder portals:** police.dhamrai / keraniganj / savar .dhaka.gov.bd have the bare title "থানা" and no officer cards, so those rows have a composed name ("<upazila> থানা") and no contacts.
- **Missing thanas:** the district has 7 upazila-area thanas; Ashulia and South Keraniganj portals (police.ashulia.dhaka.gov.bd, police.southkeraniganj.dhaka.gov.bd) failed TLS verification (certificate not trusted) and were not used. "কেরাণীগঞ্জ থানা" may stand for Keraniganj Model thana.
- police.dhaka.gov.bd publishes no thana list, contact table or circle list (its "এক নজরে" page is empty).
- Not copied: officers' names, personal e-mails, other mobiles.

## Licence
None stated → `null`.
