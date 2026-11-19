# Government offices from the national-portal sites — Chattogram

- **Sources:**
  - the office menus of chittagongdiv.gov.bd, chittagong.gov.bd and the 15 Chattogram upazila portals;
  - the 11 DC and 104 UNO portals of the division (hosts verified by page title, Nov 2026; comilla.gov.bd and chittagong.gov.bd are the hosts the portals' own menus use);
  - the Chattogram DC portal's "ইউনিয়নের তালিকা" union list.
- **Contacts:** from the office head's officer card or the "যোগাযোগ" page. Only office landlines and `*.gov.bd` e-mails are kept; mobiles, personal e-mails and officials' names are not collected.
- Licence: none stated. Accessed 2026-11-17. Key CHATTOGRAM_PORTAL_OFFICES_2026.

## Counts: 922 rows

| Where | Rows |
|---|---|
| Chattogram District: division-level offices (divisional portal menu) | 71 |
| Chattogram District: district-level offices (DC portal menu, incl. the DC office) | 65 |
| Chattogram District: upazila-level rows (UNO + upazila menus; 29–40 per upazila) | 499 |
| Chattogram District: union parishads (Patiya, Fatikchhari, Satkania 17 each … Karnaphuli 5) | 188 |
| Other districts: 10 DC + 89 UNO offices | 99 (Cumilla 18, Rangamati 11, Brahmanbaria/Noakhali/Cox's Bazar/Khagrachhari 10, Chandpur 9, Bandarban 8, Feni 7, Lakshmipur 6) |

Categories:

| Category | Rows |
|---|---|
| government | 511 |
| union_parishad | 188 |
| uno_office | 104 |
| land_office | 23 |
| police_station | 17 |
| agri_office | 16 |
| fire_station, upazila_health_complex | 13 each |
| dc_office | 11 |
| bank | 7 |
| post_office | 6 |
| training_center, pourashava_office | 4 each |
| divisional_commissioner, passport_office, sp_office, civil_surgeon, city_corporation_office (CCC) | 1 each |

**Contacts:** phone 327, e-mail 224.
- The Divisional Commissioner has both. DC offices: phone 9 of 11 (not Chattogram, Cox's Bazar), e-mail 10 of 11 (not Chattogram).
- UNO offices: phone 64 of 104, e-mail 72 of 104.

**Upazila:** `upazila_en` is set on 781 rows. 5 Chattogram offices whose name contains a CMP thana (Panchlaish 2, Kotwali, Double Mooring, Patenga) carry that metropolitan thana. বন্দর, ইপিজেড and কর্ণফুলী are excluded from this matching because they usually name the port, export zones or river.

## Changes to fetch.py
- Chattogram tables: 11 districts, 104 upazilas (HDX COD-AB v03 spellings, verified subdomains), CMP thanas.
- A `chattogram` entry in `DIVISION_TABLES`.
- `union_list_chattogram()` reads the DC union list: serial | upazila | "Nনং <union>", UP portal linked but not opened.

## Gaps and doubts
- No structured addresses or coordinates. Every office portal responded (no TLS failures this run).
- The union list has 190 entries; two UP hosts are listed twice (paduaup, dohazariup), giving 188 rows. The DC "এক নজরে" says 190 unions.
- **Pourashavas:** only Banshkhali, Chandanaish and Dohazari appear (via upazila menus), plus a generic menu entry "এক নজরে পৌরসভা". The DC "এক নজরে" names 15 pourashavas, but no pourashava list is published.
- Some phones are numbers run together at source (e.g. "02413606750241360671", "0322334458443").
- The DC "এক নজরে" lists 16 upazilas (Fatikchhari North/South); the tables use HDX's 15.
