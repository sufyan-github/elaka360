# CHATTOGRAM_POLICE_2026 — Chattogram District Police

**Source (trust level 4, accessed 2026-11-18):**
- police.chittagong.gov.bd: SP officer card and the "যোগাযোগ" address;
- the Bangladesh Police site chattogramdistrict.police.gov.bd: one page per thana (/content/255–270), each with the OC's police official mobile;
- the upazila thana portals police.<upazila>.chittagong.gov.bd: office landline and e-mail;
- the Chattogram DC portal "এক নজরে চট্টগ্রাম": thana lists.

Chattogram city is policed by CMP (CHATTOGRAM_METRO_POLICE_THANAS_2026).

**fetch.py:**
- New `main_chattogram()`.
- `sp_office_row()` takes an optional `host` (default unchanged).
- A portal "landline" that is an official mobile missing its leading 1 (e.g. 0320107605) is dropped and noted.

## Collected (17 rows)
- 1 × `government.sp_office`: পুলিশ সুপারের কার্যালয়, চট্টগ্রাম — 0241355536, SP official mobile 01320107400, spchittagong@police.gov.bd; address "৬৩ পূর্ব নাসিরাবাদ, ২ নং গেইট চট্টগ্রাম".
- 16 × `emergency.police_station`, as listed in the site menu: Sitakunda Model, Sandwip, Mirsarai, Zorarganj, Hathazari Model, Fatikchhari, Bhujpur, Rangunia Model, Raozan, Patiya, Boalkhali, Satkania, Lohagara, Anwara, Banshkhali, Chandanaish.
  - Phone on 15 of 16 (OC official mobile; landline on 5).
  - E-mail on 8 (occhi.*@police.gov.bd).
  - Zorarganj and Bhujpur are not upazilas (`upazila_en` empty).
- **facts:**
  - DC portal: 16 thanas at upazila level (it also lists 16 "মহানগর" thanas — those are CMP's);
  - 16 thana pages listed on the district police site.

## Gaps and doubts
- Mirsarai has no number (the police site page and the portal give none). Sandwip's page has no OC number; its phone is the thana portal's OC mobile (01713-37 series).
- Hathazari portal number 0320107605 (probably a mistyped 01320107605) is not used.
- Lohagara portal gives 09611211211 (an IP number) as office phone; kept as printed.
- police.karnafuli.chittagong.gov.bd is CMP's Karnaphuli thana and is not used here.
- Officers' names, personal e-mails and other mobiles are not copied.

## Licence
None stated → `null`.
