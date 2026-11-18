# MYMENSINGH_POLICE_2026 — Mymensingh District Police

**Sources (trust level 4, accessed 2026-11-18):**
- police.mymensingh.gov.bd: the SP officer card on the officer list (/pages/officers);
- the 13 upazila thana portals police.<upazila>.mymensingh.gov.bd;
- police.gov.bd's Mymensingh Range page, for the counts.

There is no metropolitan police in Mymensingh: police.gov.bd lists eight metropolitan units, none for Mymensingh, and counts Kotwali among the district police's stations.

**fetch.py:** Mymensingh tables and a new `main_mymensingh()`: SP card (officer-list fallback), the police.gov.bd facts and the thana portals.

## Collected (14 places, 4 facts)
- **1 × `government.sp_office`:** পুলিশ সুপারের কার্যালয়, ময়মনসিংহ — 01320103100 (SP official mobile); spmymensingh@police.gov.bd.
- **13 × `emergency.police_station`:** one per upazila portal. 11 have the OC's official mobile (01320-103xxx). None has a landline or e-mail.
- **facts (police.gov.bd, undated):**
  - police_stations = 14 (Kotwali, Muktagacha, Fulbaria, Pagla, Trishal, Gouripur, Ishorgonj, Nandail, Fulpur, Haluaghat, Dhubaora, Goforgaon, Valuka, Tarakanda);
  - police_circles = 4;
  - police_outposts = 2;
  - police_investigation_centres = 4.

## Gaps and doubts
- **Composed names (8):** Mymensingh Sadar, Trishal, Bhaluka, Nandail, Gouripur, Haluaghat and Dhobaura portals are titled only "থানা", so names are composed from the upazila. "ময়মনসিংহ সদর থানা" is presumably Kotwali Model Thana (police.gov.bd names no "Sadar" thana), but this is not stated.
- **Missing thana rows:** Kotwali and Pagla have no upazila thana portal, so they are not rows (counted in the fact).
- **No phone:** Bhaluka, Nandail.
- The SP portal's contact entries are empty links; its "সাংগঠনিক কাঠামো" page is empty; there is no "এক নজরে".
- The other officers' cards are not copied (several give gmail addresses). The DC menu's link mymensingh.police.gov.bd does not respond.

## Licence
None stated → `null`.
