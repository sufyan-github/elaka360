# Government offices from the national-portal sites — Barishal

- **Sources:**
  - the office menus of barisaldiv.gov.bd (divisional portal; barishaldiv.gov.bd serves the same site), barisal.gov.bd (Barishal DC portal; barishal.gov.bd serves the same site) and the 10 Barishal upazila portals;
  - the 6 DC and 42 UNO portals of the division (hosts verified by page title, Nov 2026; Jhalokathi's DC portal is jhalakathi.gov.bd, jhalokathi.gov.bd does not resolve);
  - the Barishal DC portal's "ইউনিয়নের তালিকা" union list.
- **Contacts:** from the office head's officer card or the "যোগাযোগ" page. Only office landlines and `*.gov.bd` e-mails are kept; mobiles, personal e-mails and officials' names are not collected.
- Licence: none stated. Accessed 2026-11-18. Key BARISHAL_PORTAL_OFFICES_2026.

## Counts: 618 rows

| Where | Rows |
|---|---|
| Barishal District: division-level offices (divisional portal menu, incl. the Divisional Commissioner) | 57 |
| Barishal District: district-level offices (DC portal menu, incl. the DC office) | 102 |
| Barishal District: upazila-level rows (UNO + upazila menus; 29–36 per upazila) | 334 |
| Barishal District: union parishads (Mehendiganj 16, Bakerganj 14, Barishal Sadar 10, Wazirpur 9, Banaripara 8, Gaurnadi 7, Muladi 7, Babuganj 6, Hizla 6, Agailjhara 5) | 88 |
| Other districts: 5 DC + 32 UNO offices | 37 (Patuakhali 9, Pirojpur 8, Bhola 8, Barguna 7, Jhalokathi 5) |

| Category | Rows |
|---|---|
| government | 406 |
| union_parishad | 88 |
| uno_office | 42 |
| agri_office | 13 |
| upazila_health_complex, land_office | 10 each |
| police_station | 9 |
| post_office, fire_station | 7 each |
| dc_office | 6 |
| training_center, bank | 5 each |
| college | 3 |
| sp_office (SP Barishal; BMP's national-portal site "পুলিশ কমিশনার") | 2 |
| divisional_commissioner, civil_surgeon, passport_office, city_corporation_office (BCC, barishalcity.gov.bd), pourashava_office (Muladi) | 1 each |

**Contacts:** phone 236, e-mail 147. The Divisional Commissioner has both; all 6 DC offices have both. UNO offices: phone 26 of 42, e-mail 33 of 42.

**Upazila:** `upazila_en` is set on 455 rows. No office name matched a BMP thana. Only Kotwali and Kaunia are matched, because "বন্দর" (river ports) and "এয়ারপোর্ট" are ambiguous.

## Changes to fetch.py
- Barishal tables:
  - 6 districts (seed spellings);
  - 42 upazilas (BBS/HDX-style English; portal subdomains verified by home-page title);
  - BMP thanas.
- A `barishal` entry in `DIVISION_TABLES` with `CLEAN_HREFS=True` (Barishal only):
  - doubled schemes ("http://http://youth.agailjhara…") are repaired;
  - a leading "www." is dropped on deep `*.gov.bd` hosts (Wazirpur's menu links www.<office>.wazirpur.barisal.gov.bd, which fails TLS);
  - untitled menu entries are skipped (Muladi lists its SFDF link twice, once without a title).
- `union_list_barishal()` reads serial | upazila | union count | comma-separated unions, without inserting spaces at `<span>` boundaries.

## Gaps and doubts
- No structured addresses or coordinates.
- **Did not respond, listed from the menu only:**
  - rdobarishal.gov.bd (does not resolve);
  - barz.touristpolice.gov.bd and sfdf.ro.barisal.gov.bd (self-signed TLS; skipped).
- **Pourashavas:** only Muladi's portal appears. No pourashava list is parsed.
- **Union names** are as printed, including hyphenated pairs (রায়পাশা-কড়াপুর, দরিরচর-খাজুরিয়া, হিজলা-গৌরবদি, শিকারপুর-উজিরপুর) and spellings such as "চাদপুরা". The list gives no UP portal hosts.
- **UNOs without a phone:** Bakerganj, Mehendiganj, Patuakhali Sadar, Bauphal, Mirzaganj, Galachipa, Rangabali, Nazirpur, Kawkhali, Mathbaria, Bhola Sadar, Char Fasson, Manpura, Tazumuddin, Amtali, Bamna.
- **UNOs without an e-mail:** Bakerganj, Mirzaganj, Nazirpur, Kawkhali, Zianagar, Bhandaria, Mathbaria, Bhola Sadar, Tazumuddin.
