# MYM_RANGE_POLICE_PORTALS_2026 — district police portals, Mymensingh Range (excl. Mymensingh District)

**Source (trust level 4, accessed 2026-11-18):**
- police.jamalpur / police.sherpur / police.netrokona `.gov.bd`, and each upazila's thana portal police.<upazila>.<district>.gov.bd;
- the Jamalpur SP portal's "এক নজরে পুলিশ সুপারের কার্যালয়": a table of posts with police official mobiles and police.gov.bd e-mails, no names;
- police.gov.bd's Mymensingh Range page, for the thana counts.

Mymensingh Range is led by the Range DIG's office (policedig.mymensinghdiv.gov.bd; "এক নজরে": formed by gazette of 12 Oct 2015 from the division's 4 districts). Mymensingh District is in MYMENSINGH_POLICE_2026. There is no metropolitan police in the division.

**fetch.py:** Mymensingh tables and a new `main_mymensingh()` on the Sylhet pattern (SP officer card with a fallback to the officer list; one thana portal per upazila). For Jamalpur, missing thana contacts are filled from the posts table, which also gives the river-police thana and the control room. Facts come from police.gov.bd.

## Collected: 27 rows, 2 facts

| District | Rows | Thanas with phone / e-mail |
|---|---|---|
| Jamalpur | 10 (SP, 7 thanas, Bahadurabad Ghat river-police thana, control room) | 8 of 8 / 7 of 8 |
| Netrokona | 11 (SP, 10 thanas) | 8 of 10 / 2 of 10 |
| Sherpur | 6 (SP, 5 thanas) | 2 of 5 / 0 |

- **3 × `government.sp_office`:**
  - Jamalpur: 098162143; 01320105100; spjamalpur@police.gov.bd
  - Sherpur: 01320106100; spsherpur@police.gov.bd
  - Netrokona: 095161543; 01320104100; spnetrokona@police.gov.bd
- **Jamalpur thanas:** the OC official mobiles (01320-105xxx) and ocjam.*@police.gov.bd e-mails come from the portal cards and the posts table (noted per row). The river-police thana has 01713373545 (police series); upazila not stated.
- **Facts:** police_stations Jamalpur = 8 (incl. Bahadurabad), Netrokona = 10 (police.gov.bd, undated).

## Contact rule
- Office landlines, police official mobiles, `*.gov.bd` e-mails only.
- No names, personal e-mails or other mobiles. Circle ASP and other posts in the Jamalpur table are not rows.

## Gaps and doubts
- **No phone:** Sreebordi, Nokla, Jhenaigati, Kalmakanda, Netrokona Model (e-mail only). Their portals have no OC card.
- **Not used:** Netrokona's "থানা ও ফাঁড়ির ইনচার্জদের ফোন নাম্বার" is a single image. Sherpur's "এক নজরে" gives district statistics but no thana count; police.gov.bd gives only its 1984 founding count (5), which is not used.
- Cards are self-maintained and may be outdated. Thanas that are not upazilas have no portal.

## Licence
None stated → `null`.
