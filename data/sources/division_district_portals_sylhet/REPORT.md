# District portals of the other three districts (Sylhet Division)

- **Collector:** `division_district_portals/fetch.py --division sylhet`.
- **Hosts:** moulvibazar, habiganj and sunamganj `.gov.bd`. Each is confirmed by its home-page title ("হোম | <জেলা> জেলা") and by the national office registry.
- **Pages:** found from each menu. 12 pages, all fetched (`raw/pages.csv`, texts in `raw/`).
- **areas.csv (274):** 3 districts, 28 upazilas (all with website), 232 unions, 11 pourashavas.
- **facts.csv (57):** এক নজরে figures, stated counts and listed counts.

| District | Upazilas listed (stated) | Unions listed (stated) | Union links on list | From registry | Pourashavas named (stated) |
|---|---|---|---|---|---|
| Moulvibazar | 7 (7) | 67 (67) | 0 | 65 | 5 (5) |
| Habiganj | 9 (9) | 78 (78) | 0 | 63 | 6 (6) |
| Sunamganj | 11 + Sadar (12) | 87 (88) | 0 | 74 | 0 (4) |

## Layouts, gaps and conflicts

- **Moulvibazar:**
  - The menu items are "উপজেলা পরিষদ" (2026-05-24: 7 "X উপজেলা পরিষদ" rows) and "ইউনিয়ন পরিষদ" (2026-04-19).
  - The union table is "উপজেলা | সংখ্যা | names", one "০১ নং X ইউনিয়ন পরিষদ" per line. The union numbers are kept as `code`.
  - The Sadar upazila is printed "মৌলভীবাজার" (the district's name). It is read as Moulvibazar Sadar, noted per row.
  - Pourashavas: from এক নজরে "পৌরসভার সংখ্যা | : | ০৫ টি (মৌলভীবাজার, শ্রীমঙ্গল, কুলাউড়া, বড়লেখা, কমলগঞ্জ)". মৌলভীবাজার পৌরসভা has the website moulvibazar.paurasheba.com from a menu link.
  - No registry match, so no website: মোস্তফাপুর, শমসেরনগর (registry শমশেরনগর).
  - Figures: area 2,799 km², population 2,122,703 (2022).
- **Habiganj:**
  - "উপজেলা ও ইউনিয়ন" (2019-02-19) is used as the upazila list (9, linked).
  - "ইউনিয়নের তালিকা" (2026-07-08) is a table "ক্র | জেলা | উপজেলা | ইউনিয়ন" with 78 rows.
  - Sadar lists নূরপুর and শায়েস্তাগঞ্জ (9). Both are also listed under Shayestaganj, where the registry has them: DOUBT notes.
  - Ajmiriganj 4 (no কাকাইলছেও; registry 5). Nabiganj 13 (পূর্ব/পশ্চিম বড়ভাকৈড়; registry 12).
  - 15 unions have no website, because of spelling variants: পৈল/পইল, রাজিউরা/রাজিউড়া, বুলা/বুল্লা, মুড়াকুরি/মোড়াকরি, দীঘলবাগ/দীঘলবাক, লামাতাসী/লামাতাশী, বড়ইউরি/বড়ইউড়ি, "উত্তর পূর্ব বানিয়াচং"/"বানিয়াচং উত্তর পূর্ব" (×4), plus the two duplicates.
  - Area: "২৬৩৬. ৫৮" is read as 2,636.58 km² (noted). Population 2,358,886 has no year ("সর্বশেষ আদমশুমারী অনুযায়ী সমন্বিত").
  - Pourashavas: 6 from এক নজরে. হবিগঞ্জ পৌরসভা has the website habiganjpourashava.gov.bd from a menu link.
- **Sunamganj:**
  - One page, "উপজেলা ও ইউনিয়ন" (2023-01-03), serves as both the upazila and the union list.
  - Sadar is printed "সুনামগঞ্জ" (read as Sunamganj Sadar, noted); South Sunamganj is printed শান্তিগঞ্জ.
  - The upazila list counter finds 11; Sadar is added from the union rows.
  - Upazila portals are not linked; all 12 were verified by fetching them (titles in notes).
  - **Madhyanagar 4** (মধ্যনগর, চামারদানী, বংশীকুন্ডা(দঃ), বংশীকুন্ডা(উঃ)). The registry still has these under Dharmapasha (10) and none under Madhyanagar. The DC lists Dharmapasha with 6. মধ্যনগর has a DOUBT note.
  - Jamalganj 5 (registry 6).
  - Bishwambarpur prints বাদাঘাট(দঃ); Tahirpur has বাদাঘাট.
  - এক নজরে says "পৌরসভা | ৪টি" without names, so no pourashava rows.
  - 13 unions have no website (spelling variants, and the 4 Madhyanagar unions).
- **Union websites:** none of the lists links union portals. Websites are from the national registry (same district, upazila and name; noted per row). Links were not guessed.
- Raw page texts have phone numbers and e-mails redacted.

## Licence

No licence stated; facts only. Attribution: জেলা প্রশাসন, সিলেট বিভাগ — জাতীয় তথ্য বাতায়ন (<district>.gov.bd).
