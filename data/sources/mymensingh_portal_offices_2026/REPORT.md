# Government offices from the national-portal sites — Mymensingh

- **Sources:**
  - the office menus of mymensinghdiv.gov.bd (divisional portal), mymensingh.gov.bd (Mymensingh DC portal) and the 13 Mymensingh upazila portals;
  - the 4 DC and 35 UNO portals of the division (hosts verified by page title, Nov 2026: "হোম | <জেলা> জেলা", "হোম | <উপজেলা> উপজেলা"; subdomains as in the seed, e.g. dewangonj.jamalpur.gov.bd, sreebordi.sherpur.gov.bd, mohongonj.netrokona.gov.bd);
  - the Mymensingh DC portal's "উপজেলা ও ইউনিয়নের তালিকা" (/pages/static-pages/6973bef4c4774958d7bc1029), checked against the upazila portals' "ইউনিয়ন সমূহ" pages.
- **Contacts:** from the office head's officer card or the "যোগাযোগ" page. Only office landlines and `*.gov.bd` e-mails are kept; mobiles, personal e-mails and officials' names are not collected.
- **TLS:** all hosts use Sectigo DV R36, whose intermediate the collector already adds; verification stays on.
- Licence: none stated. Accessed 2026-11-18. Key MYMENSINGH_PORTAL_OFFICES_2026.

## Counts: 775 rows

| Where | Rows |
|---|---|
| Division-level offices (divisional portal menu, incl. the Divisional Commissioner) | 60 (phone 36, e-mail 18) |
| Mymensingh District: district-level offices (DC portal menu, incl. the DC office) | 99 (phone 62, e-mail 28) |
| Mymensingh District: upazila-level rows (UNO + upazila menus; 28–41 per upazila) | 455 (phone 130, e-mail 86) |
| Mymensingh District: union parishads (Gafargaon 15, Fulbaria 13, Nandail 13, Trishal 12, Mymensingh Sadar 11, Bhaluka 11, Iswarganj 11, Muktagacha 10, Haluaghat 10, Tarakanda 9, Gouripur 8, Dhobaura 7, Phulpur 6) | 136 |
| Other districts: 3 DC + 22 UNO offices | 25 (Netrokona 11, Jamalpur 8, Sherpur 6) |

| Category | Rows |
|---|---|
| government | 493 |
| union_parishad | 136 |
| uno_office | 35 |
| agri_office | 15 |
| upazila_health_complex | 14 |
| training_center, police_station, land_office | 13 each |
| fire_station | 12 |
| post_office | 9 |
| bank (Palli Sanchay Bank branches) | 5 |
| dc_office, pourashava_office | 4 each |
| college | 3 |
| passport_office | 2 |
| divisional_commissioner, city_corporation_office (MCC, mcc.gov.bd), sp_office, civil_surgeon | 1 each |

**Contacts:** phone 245, e-mail 149. The Divisional Commissioner and all 4 DC offices have both. UNO offices: phone 22 of 35, e-mail 25 of 35.

**Upazila:** `upazila_en` is set on 613 rows. There is no Mymensingh Metropolitan Police, so no office is mapped to a metropolitan thana.

## Changes to fetch.py
- Mymensingh tables: 4 districts and 35 upazilas (seed English spellings, Bangla aliases NFC-normalised, verified subdomains); an empty metro-thana table.
- A `mymensingh` entry in `DIVISION_TABLES`, with `CLEAN_HREFS` (as for Barishal) and the alias www.mcc.gov.bd → mcc.gov.bd.
- `union_list_mymensingh()`: the DC list gives the upazila as a merged cell, so the rowspan is followed. Rows outside every upazila cell, or rows the upazila's own portal does not list while exactly one other upazila portal does, take the upazila from the upazila portals' "ইউনিয়ন সমূহ" pages. This is noted per row, with the DC-list value in `extra_json`.
- Mymensingh only:
  - bullets in menu titles ("●") are dropped, with the title as listed in `extra_json`;
  - a bare "পৌরসভা" / "থানা" title becomes "<upazila> পৌরসভা" / "<upazila> থানা" (11 rows, noted);
  - offices whose portal failed TLS are noted with the reason;
  - www.bdlaws.gov.bd (a law-database link in the Fulbaria menu) is not an office;
  - a leading "-" in e-mails is dropped (Nokla UNO card: "-unonakhla@mopa.gov.bd").
- No arguments still writes the committed Rajshahi places.csv: the HEAD code and the new code give identical output on the same pages. A live run differs from the committed file in 16 rows because officer cards on the sites have changed.

## Gaps and doubts
- **Union list:**
  - The list has 136 of the district's unions (the DC "এক নজরে" says 145). Phulpur lists 6 and Dhobaura 7. Haluaghat's ভূবনকুড়া and শাকুয়াই and Tarakanda's গালাগাঁও are missing.
  - **Haluaghat:** the list has no upazila cell for 9 unions (গাজিরভিটা … হালুয়াঘাট). The Tarakanda cell's 10-row span covers জুগলী, but the Haluaghat portal lists it and Tarakanda's does not. All 10 rows take Haluaghat from the Haluaghat portal's union page (noted).
  - No UP portal links are given and no contacts are collected.
- **Menu links to www.<office>…gov.bd** (self-signed certificates) are read as the hosts without "www.", as for Barishal.
- **TLS failures, skipped and noted:** bida.gov.bd (handshake failure), sfdf.ro.mymensingh.gov.bd (self-signed) and www.trishalpourashava.org (TLS error).
- **SP link:** the DC menu's SP link mymensingh.police.gov.bd did not respond; the SP portal is police.mymensingh.gov.bd (see MYMENSINGH_POLICE_2026).
- **Composed name:** the composed "ময়মনসিংহ সদর থানা" is likely Kotwali Model Thana, but no source here says so.
- **Phones longer than a normal landline, kept as published:** 022996667228, 022996664365, 0902996677115, 0202996674248, 029966755780, and 029977777114 (Islampur UNO).
- MCC's head card gives only mayor@mcc.gov.bd.
- "পল্লী সঞ্চয় ব্যাংক" offices fall under finance.bank (same rules as the other divisions).
