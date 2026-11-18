# BARISHAL_POLICE_2026 — Barishal District Police

**Sources (trust level 4, accessed 2026-11-18):**
- police.barisal.gov.bd:
  - the SP officer card;
  - the officer list (/pages/officers, which also carries the 10 thana OCs' cards);
  - the menu "থানা / অন্যান্ন কার্যালয়সমূহ" (10 thanas);
  - "ডাক যোগাযোগ" (address);
  - "যোগাযোগ" (an English contact table, content updated 26 Apr 2018).
- The 9 upazila thana portals police.<upazila>.barisal.gov.bd.

Barishal city is policed by BMP (BARISHAL_METRO_POLICE_THANAS_2026).

**fetch.py:** new `main_barishal()`. For each thana, numbers are taken from the thana portal's own officer cards first. Gaps are filled from the thana OC's card on the SP officer list, then from the 2018 table. Rules for the SP list:
- an e-mail is kept only if it is that thana's mailbox (`ocbar.<code>`);
- a mobile is kept only if no other thana's OC card carries the same number.

## Collected (12 rows)
- **1 × `government.sp_office`:** পুলিশ সুপারের কার্যালয়, বরিশাল — 043164846; 01320151100; spbarisal@police.gov.bd. Address: পলিট্যাকনিক রোড, আলেকান্দা, বরিশাল-৮২০০.
- **10 × `emergency.police_station`** (the SP menu's 10 thanas):
  - the 9 upazila thanas: Bakerganj, Babuganj, Wazirpur ("উজিরপুর মডেল থানা"), Banaripara, Gaurnadi, Agailjhara, Mehendiganj, Muladi, Hizla;
  - কাজিরহাট থানা, which has no upazila portal; it is listed in the menu with a link to barisal.police.gov.bd (not opened). Its contacts (01320151420, ocbar.kaz@police.gov.bd) come from the OC card. `upazila_en` is empty because no source names its upazila.
  - All 10 have a phone and a `*.gov.bd` e-mail.
- **1 × `emergency`:** বরিশাল জেলা পুলিশ কন্ট্রোল রুম, landline 043163780 (2018 table; its mobile is not an official-series number and is not copied).
- **facts:** police_stations = 10 (SP menu, 2026; the 2018 table has the same 10 OC rows).

## Gaps and doubts
- police.barisalsadar.barisal.gov.bd is titled "বরিশাল সদর থানা" but has no content and is not in the SP menu or table, so it is not a row.
- The SP officer list mixes cards up:
  - the Muladi OC card carries Bakerganj's mailbox (dropped);
  - Bakerganj's and Babuganj's Bangla OC cards share one mobile, 01320151186. It is kept only for Bakerganj, whose own portal shows it. Babuganj keeps its landline 0432773322; its English card lists 01320151212, which is not used.
- Agailjhara's and Muladi's portals still show old 01713-374xxx mobiles; the SP list has 01320-151xxx numbers (both kept in `extra_json`).
- The 2018 table is outdated and is used only as a fallback.
- Officers' names are not copied; raw/ keeps only the rows used.

## Licence
None stated → `null`.
