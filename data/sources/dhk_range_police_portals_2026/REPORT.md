# DHK_RANGE_POLICE_PORTALS_2026 — district police portals, Dhaka Range (excl. Dhaka District)

**Source (trust level 4, accessed 2026-11-17):** police.<district>.gov.bd for Narsingdi, Gazipur, Shariatpur, Narayanganj, Tangail, Kishoreganj, Manikganj, Munshiganj, Rajbari, Madaripur, Gopalganj, Faridpur, and each thana's own portal police.<upazila>.<district>.gov.bd (2026 national-portal framework). Dhaka District is in DHAKA_POLICE_2026; GMP thanas are in GAZIPUR_METRO_POLICE_THANAS_2026.

**fetch.py:** new `main_dhaka()` on the Rangpur pattern (SP officer card + one portal per upazila thana), with per-district extras: Gazipur's thana-website list (and Joydebpur thana's own host for Gazipur Sadar), the Narayanganj and Kishoreganj unit counts. Shared helpers: better thana names from portal titles, "Site is not available" placeholders skipped.

| District | Rows | Thanas with phone / e-mail |
|---|---|---|
| Kishoreganj | 14 | 11 / 9 of 13 |
| Tangail | 13 | 8 / 4 of 12 |
| Faridpur | 10 | 5 / 1 of 9 |
| Narsingdi | 7 | 5 / 3 of 6 |
| Shariatpur | 7 | 5 / 0 of 6 |
| Manikganj | 7 | 5 / 0 of 6 |
| Munshiganj | 7 | 5 / 4 of 6 |
| Rajbari | 6 | 3 / 1 of 5 |
| Gazipur | 6 | 4 / 3 of 5 |
| Narayanganj | 6 | 1 / 1 of 5 |
| Madaripur | 5 | 3 / 0 of 4 |
| Gopalganj | 5 | 4 / 3 of 4 |

Categories: 81 `emergency.police_station`, 12 `government.sp_office` (all 12 with phone and `@police.gov.bd` e-mail).

facts (9 rows): Gazipur 5 district-police thanas listed; Narayanganj 7 thanas, 12 outposts, 3 investigation centres, 2 circles; Kishoreganj 13 thanas, 6 circles, 6 investigation centres, 4 outposts.

## Contact rule
- **SP offices:** Superintendent's officer card — office landline, the SP's police official mobile (01320-xxx300), `*@police.gov.bd`, fax in `extra_json`.
- **Thanas:** office landline and the officer-in-charge's police official mobile (01320-xxxxxx or the older 01713-37/38xxxx police CUG series; 8 rows use the latter); only `*.gov.bd` e-mails. Other mobiles, personal e-mails and names are not copied.

## Coverage and doubts
- **Coverage:** phone on 71 of 93 rows, e-mail on 41; no addresses or coordinates.
- **No phone (22 thanas):** their portals have no OC card, only personal numbers, or no cards at all (e.g. Manohardi, Naria, Dhanbari, Ghatail, Madhupur, Mirzapur, Araihazar, Rupganj, Sonargaon, Boalmari, Faridpur Sadar).
- **Names composed** from the upazila where the portal title is a bare "থানা" (43 rows; noted per row).
- **Not covered:** Singair and Muksudpur thana portals failed TLS verification (self-signed certificate), Dasar's portal is a "Site is not available" placeholder. Thanas that are not upazilas (e.g. Narayanganj's Fatullah and Siddhirganj — the district has 7 thanas but 5 upazilas) have no portal found.
- **Gazipur:** the district police list names 5 thanas (Joydebpur for Gazipur Sadar); police.sadar.gazipur.gov.bd was replaced by Joydebpur thana's own portal joydebpurpolice.sadar.gazipur.gov.bd.
- Cards are self-maintained and may be outdated.

## Licence
None stated → `null`.
