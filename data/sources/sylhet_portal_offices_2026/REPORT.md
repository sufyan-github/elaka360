# Government offices from the national-portal sites — Sylhet

- **Sources:**
  - the office menus of sylhetdiv.gov.bd (divisional portal), sylhet.gov.bd (Sylhet DC portal) and the 13 Sylhet upazila portals;
  - the 4 DC and 41 UNO portals of the division (hosts verified by page title, Nov 2026; upazila subdomains from the national office registry, e.g. kamolganj.moulvibazar.gov.bd, sadar.sunamganj.gov.bd, shantiganj.sunamganj.gov.bd for the seed's South Sunamganj);
  - the Sylhet DC portal's "ইউনিয়নের তালিকা" (/pages/static-pages/696cb362c4774958d7ba0694).
- **Contacts:** from the office head's officer card or the "যোগাযোগ" page. Only office landlines and `*.gov.bd` e-mails are kept; mobiles, personal e-mails and officials' names are not collected.
- **TLS:** sylhet.gov.bd and its sub-sites send only their leaf certificate. The Let's Encrypt intermediates are added from the CA's AIA URLs for Sylhet runs; verification stays on.
- Licence: none stated. Accessed 2026-11-18. Key SYLHET_PORTAL_OFFICES_2026.

## Counts: 742 rows

| Where | Rows |
|---|---|
| Division-level offices (divisional portal menu, incl. the Divisional Commissioner) | 71 (phone 42, e-mail 28) |
| Sylhet District: district-level offices (DC portal menu, incl. the DC office) | 95 (phone 67, e-mail 32) |
| Sylhet District: upazila-level rows (UNO + upazila menus; 28–41 per upazila) | 439 |
| Sylhet District: union parishads (Gowainghat 13, Golapganj 11, Beanibazar 10, Zakiganj 9, Kanaighat 9, Dakshin Surma 8, Bishwanath 8, Osmaninagar 8, Sylhet Sadar 7, Jaintiapur 6, Companiganj 6, Balaganj 6, Fenchuganj 5) | 106 |
| Other districts: 3 DC + 28 UNO offices | 31 (Sunamganj 13, Habiganj 10, Moulvibazar 8) |

| Category | Rows |
|---|---|
| government | 499 |
| union_parishad | 106 |
| uno_office | 41 |
| agri_office | 15 |
| upazila_health_complex, land_office | 13 each |
| fire_station, police_station | 10 each |
| training_center | 8 |
| post_office | 6 |
| bank, dc_office | 4 each |
| court, college | 3 each |
| sp_office (SP Sylhet; SMP's national-portal site "পুলিশ কমিশনার"), passport_office | 2 each |
| divisional_commissioner, civil_surgeon, city_corporation_office (SCC, scc.gov.bd) | 1 each |

**Contacts:** phone 135, e-mail 92. The Divisional Commissioner and all 4 DC offices have both. UNO offices: phone 23 of 41, e-mail 29 of 41.

**Upazila:** `upazila_en` is set on 573 rows. No office name matched an SMP thana. Only Kotwali is matched: জালালাবাদ and মোগলাবাজার are also union names (and Jalalabad Gas), শাহপরান names shrines, দক্ষিণ সুরমা is also the upazila.

## Changes to fetch.py
- Sylhet tables: 4 districts and 41 upazilas (seed English spellings, Bangla aliases, verified subdomains), SMP thanas, Let's Encrypt intermediates.
- A `sylhet` entry in `DIVISION_TABLES`.
- `union_list_sylhet()`: rows are (upazila on first row | union | UP portal host printed as text). Numbers printed as "১নং" / "০১" / "২ নং" are parsed and the "ইউনিয়ন পরিষদ" / "ইউ/পি" suffix is dropped. A host printed for an earlier union is not reused.
- Sylhet only:
  - request errors are kept, so offices whose sub-site failed TLS are noted "TLS certificate hostname mismatch";
  - decorative marks in menu titles ("*", "►►") are dropped, with the title as listed kept in `extra_json`;
  - a bare "থানা" title becomes "<upazila> থানা".
- No arguments still writes the committed Rajshahi places.csv: the HEAD code and the new code give identical output on the same pages. A live run differs in 16 rows from site updates.

## Gaps and doubts
- **428 rows (426 upazila-level, 2 district-level) have no contacts.** The sub-sites x.<upazila>.sylhet.gov.bd serve the `*.sylhet.gov.bd` certificate, which does not cover them, so they were skipped. These rows are listed from the menus with a note. One divisional-menu office (bi.sylhetdiv.gov.bd) did not respond.
- **Union list:**
  - it gives Osmaninagar's পশ্চিম পৈলনপুর the host of উমরপুর, so no website is kept for that row;
  - 3 unions have no host (মধ্য জাফলং, বিছনাকন্দি and one other), and 5 hosts are printed but not linked;
  - Sylhet Sadar lists 7 unions; names are as printed (e.g. "ইসলাম পশ্চিম").
- **SCC's head card** gives 02996643266, the same number as the Divisional Commissioner's card. It is kept as published.
- No pourashava is linked in the Sylhet menus.
- "পল্লী সঞ্চয় ব্যাংক" offices fall under finance.bank (same rules as the other divisions).
