# Government offices from the national-portal sites — Khulna

- **Sources:**
  - the office menus of khulnadiv.gov.bd, khulna.gov.bd and the 9 Khulna upazila portals;
  - the 10 DC and 59 UNO portals of the division (hosts verified by page title, Nov 2026; jessore.gov.bd is the host the Jashore portals use — the divisional menu's jashore.gov.bd link is treated as the same site);
  - the Khulna DC portal's "ইউনিয়ন পরিষদসমূহের তালিকা" union list.
- **Contacts:** from the office head's officer card or the "যোগাযোগ" page. Only office landlines and `*.gov.bd` e-mails are kept; mobiles, personal e-mails and officials' names are not collected.
- Licence: none stated. Accessed 2026-11-18. Key KHULNA_PORTAL_OFFICES_2026.

## Counts: 617 rows

| Where | Rows |
|---|---|
| Khulna District: division-level offices (divisional portal menu, incl. the Divisional Commissioner) | 77 |
| Khulna District: district-level offices (DC portal menu, incl. the DC office) | 119 |
| Khulna District: upazila-level rows (UNO + upazila menus; 30–35 per upazila) | 293 |
| Khulna District: union parishads (Dumuria 14, Paikgachha 10, Dacope 9 … Phultala 4) | 68 |
| Other districts: 9 DC + 50 UNO offices, + 1 divisional-menu office (Social Forestry, cforest.jessore.gov.bd → Jashore) | 60 (Jashore 10, Bagerhat 10, Satkhira 8, Kushtia 7, Jhenaidah 7, Magura 5, Chuadanga 5, Narail 4, Meherpur 4) |

Categories:

| Category | Rows |
|---|---|
| government | 399 |
| union_parishad | 68 |
| uno_office | 59 |
| training_center | 13 |
| agri_office | 12 |
| post_office, dc_office, land_office | 10 each |
| police_station, upazila_health_complex | 9 each |
| bank | 6 |
| fire_station | 4 |
| passport_office | 2 |
| divisional_commissioner, sp_office, college, civil_surgeon, city_corporation_office (KCC), pourashava_office (Chalna) | 1 each |

**Contacts:** phone 344, e-mail 186.
- The Divisional Commissioner has both. DC offices: phone and e-mail on all 10.
- UNO offices: phone 45 of 59, e-mail 49 of 59.

**Upazila:** `upazila_en` is set on 424 rows. 5 Khulna offices whose name contains a KMP thana (Daulatpur 2, Khalishpur 3) carry that metropolitan thana. 'খুলনা' itself is not matched.

## Changes to fetch.py
- Khulna tables: 10 districts, 59 upazilas (HDX COD-AB v03 spellings, verified subdomains), KMP thanas.
- A `khulna` entry in `DIVISION_TABLES`, with `HOST_ALIASES` (jashore.gov.bd → jessore.gov.bd, so the Jashore DC office is one row) and `UPAZILA_SUB_ALIASES` (Dacope's UNO portal is dakop.khulna.gov.bd but its office sub-sites are x.dacope.khulna.gov.bd). Both are empty for the other divisions.
- `union_list_khulna()` reads the DC union list: serial | upazila (first row only) | union; no UP portal links.

## Gaps and doubts
- No structured addresses or coordinates.
- **Did not respond, listed from the menu only:**
  - kmp.police.gov.bd (HTTP 500);
  - khulnacity.gov.bd (does not resolve);
  - www.zpkhulna.gov.bd (does not resolve);
  - pourashava.dakop.khulna.gov.bd (TLS handshake failure).
- **Pourashavas:** only Chalna appears (via the Dacope menu). The DC portal's "পৌরসভার তালিকা" page is not parsed.
- **Union names** are as printed, some without spaces ("উত্তরবেদকাশী") or misspelt ("তেরখাদ"). The list has 68 unions and no UP portal hosts.
- **Satkhira DC:** the e-mail comes from the office-head card and is adcgsatkhira@mopa.gov.bd (an ADC address).
- **UNOs without a phone:** Kalaroa, Kaliganj (Satkhira), Shyamnagar, Tala, Gangni, Meherpur Sadar, Damurhuda, Magura Sadar, Bagerhat Sadar, Kachua, Mollahat, Morelganj, Sharankhola, Maheshpur.
- **UNOs without an e-mail:** Phultala, Terokhada, Chaugachha, Kaliganj (Satkhira), Shyamnagar, Magura Sadar, Mohammadpur, Shalikha, Chitalmari, Morelganj.
