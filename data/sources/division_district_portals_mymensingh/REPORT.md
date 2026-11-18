# District portals of the other three districts (Mymensingh Division)

- **Collector:** `division_district_portals/fetch.py --division mymensingh`.
- **Hosts:** jamalpur, sherpur and netrokona `.gov.bd`. Each is confirmed by its home-page title ("হোম | <জেলা> জেলা") and by the national office registry.
- **Pages:** found from each menu. 13 pages, all fetched (`raw/pages.csv`, texts in `raw/`).
- **areas.csv (244):** 3 districts, 22 upazilas (all with website), 206 unions, 13 pourashavas.
- **facts.csv (43):** এক নজরে figures, stated counts and listed counts.

| District | Upazilas listed (stated) | Unions listed (stated) | Union links on list | From registry | Pourashavas named (stated) |
|---|---|---|---|---|---|
| Jamalpur | 7 (7) | 68 (–) | 0 | 57 | 8 (8) |
| Sherpur | 5 (5) | 52 (52) | 0 | 48 | 4 (4) |
| Netrokona | 10 (title ১০টি) | 86 (title ৮৬টি) | 77 | 9 | 1 (–) |

## Layouts, gaps and conflicts

- **Jamalpur:**
  - Pages: "উপজেলার তালিকা" (page "উপজেলা সমুহ", 2026-10-13), "ইউনিয়নের তালিকা" (2026-10-13) and "অন্যান্য পৌরসভার তালিকা" (2026-10-13).
  - **Union table:** "ক্র.নং | উপজেলা | ইউনিয়ন পরিষদ", one row per upazila. The upazila name links its portal; the unions are a list inside one cell (`<ol><li>` items; Bokshiganj as a comma list). Bokshiganj is printed বক্সীগঞ্জ.
  - 68 unions (registry 68, seed 68). 11 have no registry match, so no website: বকশীগঞ্জ, ধনুয়া কামালপুর, চরপুঠিমারী, পার্থশী, নুরূন্দি, তিতপল্যা, তুলসীরচর, চরপাকেরধা, করইচরা, ভাতারা, দোয়াইল.
  - **Pourashavas:** the list page is titled "পৌরসভার মেয়র ও সচিবগণের তথ্য", but it prints only pourashava names and addresses (no people), so it is used: 8 rows.
    - Websites used: জামালপুর (jamalpurpourashava.org, also a menu link) and হাজরাবাড়ী (hazrabaripourashava.melandah.jamalpur.gov.bd).
    - The other six print their upazila's portal (e.g. melandah.jamalpur.gov.bd, www.islampur.jamalpur.gov.bd). These are not used (noted).
    - হাজরাবাড়ী's parent upazila is not stated.
  - এক নজরে: area 2,031.98 km², population 2,499,737 (2022), 7 upazilas, 8 pourashavas, 844 mouzas.
- **Sherpur:**
  - Pages: "উপজেলা ও ইউনিয়ন" (2026-07-02) as the upazila list and "ইউনিয়নের তালিকা" (2026-07-02).
  - The upazila list prints "শ্রীবদী উপজেলা" (read as Sreebordi, DOUBT: misprint). No upazila portals are linked; all 5 were verified by fetching them.
  - **Union table:** "ইউনিয়ন নং | উপজেলার নাম | বিদ্যমান ইউনিয়নের নাম (বাংলা) | (ইংরেজি)". The number runs 01–52 across the district (a serial, not used as a code). The English names are printed and kept as `name_en` (52).
  - 52 unions ("মোট ইউনিয়নঃ ৫২"); 48 websites from the registry. No website (spelling variants): ঝিনাইগাতী সদর, রাজনগর, রামচন্দ্রকুড়া মন্ডলিয়াপাড়া, যোগানিয়া.
  - **Pourashavas:** 4 from এক নজরে "পৌরসভা | ৪ (শেরপুর, নকলা, নালিতাবাড়ি, শ্রীবরদী)"; no websites.
  - এক নজরে: area 1,363.76 km², population 1,501,853 (no year), 396,149 households, 5 upazilas, 4 pourashavas, 52 unions, 678 villages, 457 mouzas.
- **Netrokona:**
  - Menu items "উপজেলা সমূহ" ("নেত্রকোণা জেলার ১০টি উপজেলাসমূহ", 2026-10-05) and "ইউনিয়ন সমূহ" ("নেত্রকোণা জেলার ৮৬টি ইউনিয়ন সমূহ", 2026-10-05).
  - Both tables end with a "ওয়েব সাইট লিংক" column, which is read as the link.
  - **Unions:** "১ নং X ইউনিয়ন পরিষদ", so the union numbers are kept as `code` (86).
    - 77 links are used.
    - 9 link to union portals in other districts (e.g. modonpurup.narayanganj.gov.bd, gazipurup.gazipur.gov.bd, gajariaup.munshiganj.gov.bd). These are not used; their websites come from the registry (noted).
  - "এক নজরে নেত্রকোণা" (page "সাধারণ তথ্যাবলীঃ") holds only an attached file, which was not downloaded: no figures.
  - **Pourashavas:** 1, from the menu link "নেত্রকোনা পৌরসভা" (netrakonapourashava.com). The divisional portal says Netrokona has 5.
- **Union websites:** where a list links none, they come from the national registry (same district, upazila and name; noted per row). Links were not guessed.
- **Against other sources:** the divisional এক নজরে gives Jamalpur 67 unions; this list, the registry and the seed have 68. All three districts match the registry per upazila.
- Raw page texts have phone numbers and e-mails redacted.

## Licence

No licence stated; facts only. Attribution: জেলা প্রশাসন, ময়মনসিংহ বিভাগ — জাতীয় তথ্য বাতায়ন (<district>.gov.bd).
