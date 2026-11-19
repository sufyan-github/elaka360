# District portals of the other twelve districts (Dhaka Division)

- **Collector:** `division_district_portals/fetch.py --division dhaka`.
- **Hosts:** narsingdi, gazipur, shariatpur, narayanganj, tangail, kishoreganj, manikganj, munshiganj, rajbari,
  madaripur, gopalganj and faridpur `.gov.bd`. Each is linked from the dhakadiv.gov.bd menu ("জেলা প্রশাসকের কার্যালয়,
  <জেলা>") and confirmed by its home-page title "হোম | <জেলা> জেলা".
- **Pages:** found from each menu: এক নজরে, উপজেলার তালিকা, ইউনিয়নের তালিকা / উপজেলা ও ইউনিয়ন, পৌরসভার তালিকা.
  46 pages, all fetched (`raw/pages.csv`, texts in `raw/`, `raw/warnings.txt`).
- **areas.csv (796):** 12 districts, 79 upazilas (all with a website), 676 unions, 29 pourashavas.
- **facts.csv (171):** এক নজরে figures, stated counts and listed counts.

| District | Upazilas | Unions listed (stated) | Union portal links | Pourashavas named (stated) |
|---|---|---|---|---|
| Narsingdi | 6 | 71 (71) | 71 | 6 (6) |
| Gazipur | 5 | 39 (39) | 38 | 3 (3) |
| Shariatpur | 6 | 65 (65) | 65 | 6 (6) |
| Narayanganj | 5 | 39 (39) | 39 | 1 (5) |
| Tangail | 12 | 120 (120) | 0 | 1 (11) |
| Kishoreganj | 13 | 108 | 106 | 1 |
| Manikganj | 7 | 65 | 65 | 0 |
| Munshiganj | 6 | 68 (68) | 0 | 2 |
| Rajbari | 5 | 42 (42) | 0 | 3 |
| Madaripur | 5 | 59 (59) | 59 | 1 (4) |
| Gopalganj | 0 | – | – | 0 |
| Faridpur | 9 | 0 (81, per upazila) | – | 5 (5) |

## Gaps, conflicts and caveats

- **Gopalganj:** the portal has no upazila, union or pourashava list page. The only union-related page is a chairman
  and secretary list (personal contacts; not used). No rows except the district.
- **Faridpur:** "উপজেলা ও ইউনিয়ন এর তথ্য" gives a union count per upazila (total ৮১ টি) but no union names. These are
  stored as `union_count_stated`, and the 9 upazilas as rows.
- **Manikganj:** 55 of the 65 union names, and 6 upazila headings, are printed in the legacy Bijoy (SutonnyMJ) ASCII
  encoding (e.g. "wkevjq" = শিবালয়).
  - They were converted to Unicode by the collector, with the printed ASCII in `notes`.
  - 47 match the national list of union portals. The other 8 are spelling variants worth checking: বানিয়াজুরী,
    সিংজুরি, খলসী, দিঘলিয়া, সায়েস্তা, জামির্তা, রামকৃষ্ণপুর, বয়ড়া.
  - One heading is printed "mvUzwihv" (সাটুরিযা, a misprint of সাটুরিয়া) and is matched as Saturia.
- **No union links on the Tangail, Munshiganj and Rajbari lists** (union `website` empty).
- **Links dropped as not this district's portals:** Kapasia তরগাঁও (www.targaonup.com), and two Kishoreganj unions
  linked to other districts (e.g. ভৈরব/শ্রীনগর → sreenagarup.munshiganj.gov.bd). Each is noted on its row.
- **Narsingdi pourashavas:** the list links মাধবদী, ঘোড়াশাল, রায়পুরা, মনোহরদী and শীবপুর all to paurainfo.gov.bd.
  That shared link is not used as a website.
- **Pourashavas without a stated parent:** মাধবদী, ঘোড়াশাল and মিরকাদিম are district-level rows with `upazila_en`
  empty. The upazila portals place মিরকাদিম under Munshiganj Sadar.
- **Pourashava parents** are otherwise inferred from the same-named upazila (noted on each row).
- **Names printed by upazila heading:** Narsingdi's union list prints বেলাব for Belabo; Kishoreganj prints সদর
  (Kishoreganj Sadar).
- **Spelling:** 69 union names differ only in spelling from the national list. Kept as printed.
- **Narsingdi Raipura:** 24 unions here and on the upazila portal, while the national list also gives 24.
- **Facts:**
  - Kishoreganj, Manikganj and Munshiganj এক নজরে pages are prose, so no figures are extracted.
  - Several pages quote the 2011 census (Narsingdi, Faridpur). Shariatpur's population is "১২.৯৪ লক্ষ", converted
    to 1,294,000.
  - Madaripur's area is "বর্গ.কি.মি." with the note "(জনশুমারি ও গৃহগণনা ২০২২)".
- Raw page texts have phone numbers and e-mails redacted.

## Licence

No licence stated; facts only. Attribution: জেলা প্রশাসন, ঢাকা বিভাগ — জাতীয় তথ্য বাতায়ন (<district>.gov.bd).
