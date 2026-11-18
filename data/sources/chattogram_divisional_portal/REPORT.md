# Chattogram Divisional Commissioner portal (chittagongdiv.gov.bd)

- **Collector:** `rajshahi_divisional_portal/fetch.py --division chattogram`. Host verified by its title "হোম | চট্টগ্রাম বিভাগ". Pages from the menu:
  - এক নজরে বিভাগ (updated 2024-12-08);
  - "জেলা ও উপজেলা" (page title চট্টগ্রাম বিভাগের জেলা ও উপাজেলাসমূহ, 2024-12-08).
- The menu has no district, upazila or union list item. It links neither the DC portals nor the national list of union portals.
- The national portal's office registry (bangladesh.gov.bd/views/union-list) was fetched only for upazila portal addresses. `raw/national_portal_list.csv` keeps the 106 Chattogram upazila rows and no unions.
- **areas.csv (115):**
  - 11 districts, from the line "জেলার সংখ্যাঃ ১১টি- চট্টগ্রাম, কুমিল্লা, …". `code` is the order in that line (`CTGDIV_LIST_SERIAL`). Website is the DC portal: not linked from this page, verified by title in the DC collectors.
  - 104 upazilas, from lines such as "১. চট্টগ্রাম- (মোট ১৫টি) মীরসরাই, সীতাকুণ্ড, …". Names are as printed. Website is from the national registry (noted on each row).
  - No unions: the portal lists none.
- **facts.csv (24):**
  - division এক নজরে: area 33,904 km²; population 29,145,000 (2011 census, as quoted); 104 upazilas; 120 thanas; 62 pourashavas; 949 union parishads; 2 city corporations; 8,081 mouzas; 15,172 villages;
  - stated district count (11), per-district upazila counts ("মোট Nটি") and listed counts.

| District | Upazilas (stated) |
|---|---|
| Chattogram | 15 |
| Cox's Bazar | 9 |
| Cumilla | 17 |
| Brahmanbaria | 9 |
| Feni | 6 |
| Chandpur | 8 |
| Lakshmipur | 5 |
| Noakhali | 9 |
| Khagrachhari | 9 |
| Rangamati | 10 |
| Bandarban | 7 |

## Conflicts and caveats

- **The এক নজরে page contradicts itself:**
  - ইউনিয়ন পরিষদ ৯৪৯টি in the first list, but ৯৪৬টি in the second block and in the per-district UISC table;
  - পৌরসভা ৬২টি vs ৬১টি.
  - The first figure of each is in facts.csv; the others are in `raw/glance.txt`. The population is from the 2011 census.
- **104 upazilas, page dated 2024-12-08.** Newer upazilas are missing:
  - Bangara (Cumilla, bangara.cumilla.gov.bd), Chandraganj (Lakshmipur) and Fatikchhari Uttar (Chattogram) have portals in the national registry;
  - chattogram.gov.bd's এক নজরে says ১৬টি upazilas.
- **"সদর" only:** 10 Sadar upazilas are printed as "সদর", and Cumilla's as "আদর্শ সদর". Each is read as the district's Sadar upazila (noted).
- **Spellings kept as printed:** বোয়ালখালি, দাগনভূইঞা, লক্ষ্মীছড়ি, কোম্পানিগঞ্জ, সোনাইমুড়ি, কাউখালি, রাজস্থলি.
- The page gives per-district area and population (rounded, undated). These were not extracted.
- The registry's geo record gives "কুমিল্লা সদর দক্ষিণ" for both comillasadar and sadarsouth, with BBS code 33 for both. Registry codes are not used.

## Licence

No licence stated; facts only. Attribution: Office of the Divisional Commissioner, Chattogram (chittagongdiv.gov.bd); upazila portal addresses from the Bangladesh National Portal (bangladesh.gov.bd/views/union-list).
