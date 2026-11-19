# Government offices from the national-portal sites — Dhaka

- **Sources:**
  - office menus of dhakadiv.gov.bd, dhaka.gov.bd and the 5 Dhaka upazila portals (Dhamrai, Dohar, Keraniganj, Nawabganj, Savar);
  - the 13 DC and 89 UNO portals of the division (hosts verified by page title, Nov 2026);
  - the Dhaka DC portal's "ইউনিয়নের তালিকা" union list.
- **Contacts:** from the office head's officer card or the "যোগাযোগ" page. Only office landlines and `*.gov.bd` e-mails are kept; mobiles, personal e-mails and officials' names are not collected.
- Licence: none stated. Accessed 2026-11-17. Key DHAKA_PORTAL_OFFICES_2026.

## Counts: 585 rows

| Where | Rows |
|---|---|
| Dhaka District: division-level offices (divisional portal menu) | 117 |
| Dhaka District: district-level offices (DC portal menu) | 126 |
| Dhaka District: upazila-level rows (Dhamrai 38, Savar 38, Dohar 35, Keraniganj 32, Nawabganj 29) | 172 |
| Dhaka District: union parishads (Dhamrai 16, Nawabganj 14, Savar 12, Keraniganj 12, Dohar 8) | 62 |
| Other districts: 12 DC + 84 UNO offices, plus 12 divisional-menu offices whose portal is under that district's host (11 passport offices, 1 other) | 108 (Kishoreganj 15, Tangail 14, Faridpur 11, Manikganj 9, Narayanganj 8, Narsingdi 8, Munshiganj 8, Shariatpur 8, Gazipur 7, Gopalganj 7, Madaripur 7, Rajbari 6) |

| Category | Rows |
|---|---|
| government | 357 |
| uno_office | 89 |
| union_parishad | 62 |
| passport_office | 19 |
| dc_office | 13 |
| agri_office | 7 |
| police_station | 7 |
| land_office | 6 |
| fire_station, upazila_health_complex | 5 each |
| training_center | 3 |
| post_office, college, city_corporation_office (DNCC, DSCC), bank | 2 each |
| divisional_commissioner, sp_office, civil_surgeon, pourashava_office (Dohar) | 1 each |

**Contacts:** phone 284, e-mail 195.
- The Divisional Commissioner has both. DC offices: 11 of 13 have a phone (not Madaripur, Shariatpur) and 11 an e-mail (not Gazipur, Madaripur).
- UNO offices: e-mail 71 of 89, phone 67 of 89.

**Upazila:** `upazila_en` is set on 330 rows. 12 Dhaka offices whose name contains a DMP thana (e.g. Mirpur, Jatrabari, Gulshan, Biman Bandar) carry that metropolitan thana, as in the Rajshahi/Rangpur runs.

## Changes to fetch.py
- Dhaka tables (13 districts, 89 upazilas with HDX spellings and verified portal subdomains, 50 DMP thanas) and a `dhaka` entry in `DIVISION_TABLES`.
- For divisions after Rangpur, a menu office whose portal lies under another district's host (e.g. `doj.narayanganj.gov.bd` on dhakadiv.gov.bd) is put in that district instead of the head district. Rajshahi and Rangpur keep their original behaviour.
- `union_list_dhaka()` reads the DC union list (upazila header rows; UP host printed as text, not opened).

## Gaps and doubts
- No structured addresses or coordinates.
- 5 office portals did not respond or failed TLS verification (self-signed): zsodhaka.gov.bd, www.dncdmn / www.dncdms / www.taxeszone1 / www.taxeszone7 .dhaka.gov.bd; listed from the menu only.
- The DC union list has 62 unions, while the DC "এক নজরে" page says 86 unions; the list may be incomplete.
- Only Dohar pourashava appears (via an upazila menu); dhaka.gov.bd publishes no pourashava list (the "এক নজরে" page names Dohar, Dhamrai and Savar pourashavas).
- Menu names are kept as listed: two Dhaka thana rows are named just "থানা" / "০১। থানা" (police.dhamrai / police.dohar); short names such as "বিআরডিবি" are kept.
- Some phones are numbers run together at source (Manikganj DC "0299661039502996611822", "02224444776201", "008802223301093").
