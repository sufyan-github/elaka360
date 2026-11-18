# District portals of the other ten districts (Chattogram Division)

- **Collector:** `division_district_portals/fetch.py --division chattogram`.
- **Hosts:** comilla, feni, brahmanbaria, rangamati, noakhali, chandpur, lakshmipur, coxsbazar, khagrachhari and bandarban `.gov.bd`.
  - The divisional portal does not link them. Each is confirmed by its home-page title ("হোম | <জেলা> জেলা"; "রাঙ্গামাটি পার্বত্য জেলা") and by the national office registry.
  - cumilla.gov.bd serves the same site as comilla.gov.bd.
- **Pages:** found from each menu: এক নজরে, উপজেলার তালিকা, ইউনিয়নের তালিকা / উপজেলা ও ইউনিয়ন, পৌরসভার তালিকা. 45 pages, all fetched (`raw/pages.csv`, texts in `raw/`, `raw/warnings.txt`).
- **areas.csv (810):** 10 districts, 91 upazilas (all with website), 672 unions, 37 pourashavas.
- **facts.csv (175):** এক নজরে figures, stated counts and listed counts.

| District | Upazilas (stated) | Unions listed (stated) | Union links | Pourashavas named (stated) |
|---|---|---|---|---|
| Cumilla | 18 (18) | 198 (193) | 0 | 8 (8) |
| Feni | 6 (6) | 43 (43) | 0 | 5 (5) |
| Brahmanbaria | 9 | 98 | 28 | 5 |
| Rangamati | 10 (10) | 50 (50) | 45 | 2 (2) |
| Noakhali | 9 (9) | 0 (91) | – | 8 (8) |
| Chandpur | 8 (8) | 88 (88) | 86 | 0 (7) |
| Lakshmipur | 6 | 58 | 0 | 4 |
| Cox's Bazar | 9 (9) | 65 (71) | 6 | 0 |
| Khagrachhari | 9 (9) | 38 (38) | 38 | 3 (3) |
| Bandarban | 7 (7) | 34 (34) | 0 | 2 (2) |

## Gaps, conflicts and caveats

- **Cumilla** ("উপজেলা ও ইউনিয়ন সমুহ", one union per paragraph):
  - prints মোট ইউনিয়ন ১৯৩ but lists 198;
  - the 8 Lalmai unions (বাগমারা, ভূলইন, বেলঘর, পেরুল উত্তর/দক্ষিণ) appear under both Sadar South and Lalmai;
  - চান্দলা appears under both Barura and Brahmanpara;
  - these rows carry a DOUBT note from the national registry;
  - every link points to lalmai.comilla.gov.bd and is not used as a website;
  - the new Bangara upazila (10 unions, bangara.cumilla.gov.bd) is listed;
  - heading misprint "আর্দশ সদর" is matched as Comilla Sadar.
- **Noakhali:** the union list is a PDF, so no union rows. The এক নজরে says ৯১; the national registry has 89.
- **Cox's Bazar** (page dated 2023-10-08):
  - two tables printed side by side, read using their rowspans;
  - the list is incomplete: Pekua 2 of 7, Moheshkhali 5 of 8, Eidgaon 4 of 5 (পোকখালী printed twice);
  - the rowspan places ধলঘাটা, মাতারবাড়ী and কালারমারছড়া under Kutubdia (registry: Moheshkhali), with a DOUBT note;
  - Chakaria still has 18, including unions that are now in Eidgaon. Kept as printed;
  - the এক নজরে says ৭১.
- **Lakshmipur:** the list includes the new Chandraganj upazila (9 unions). The registry still places these under Lakshmipur Sadar (21), so they carry DOUBT notes.
  - Pourashavas come from an administrators' list ("জনাব … প্রশাসক রায়পুর পৌরসভা"); the name after "প্রশাসক" is used.
  - The এক নজরে is a file (no figures).
- **Bandarban:** the union list has chairman names and mobiles (not used; redacted in `raw/`).
  - The heading misprint নাইক্ষ্যংড়ি is matched as Naikhongchhari.
  - The এক নজরে prints its figures as a horizontal table (96 mouzas, 2,139 villages/paras, 34 unions).
- **Hill districts:**
  - Rangamati prints "মৌজার সংখ্যা ১৫৯টি (তন্মধ্যে ১৪টি বোমাং সার্কেল)", "সার্কেল ০২টি (চাকমা সার্কেল ও বোমাং সার্কেলের কিয়দংশ)" and headmen ১৫৫ জন (in `raw/`; only the mouza count is a fact);
  - Khagrachhari: 121 mouzas; Bandarban: 96 mouzas;
  - unions are listed the same way as in the plains;
  - Rangamati's list links 5 unions to other districts' portals (e.g. amtaliup.barguna.gov.bd, barkalup.chittagong.gov.bd); these are not used.
- **Brahmanbaria:**
  - the union list has no stated count;
  - the এক নজরে is mostly prose; its per-upazila union table is not read as a district count;
  - names such as বুধমত্মী, রছুলস্নাবাদ, অরম্নরাইল and কু-া look like font-conversion artefacts. Kept as printed.
- **Feni:** the menu items "উপজেলার তালিকা" and "ইউনিয়নের তালিকা" lead to the same page (উপজেলা ভিত্তিক ইউনিয়নের তালিকা). Feni Sadar skips ৩নং and Chhagalnaiya starts at ৫নং, as printed. "জি,এম, হাট" is kept as printed.
- **Chandpur:** the এক নজরে names 7 pourashavas, but the portal has no pourashava list or links, so there are no pourashava rows.
- **Pourashava parents** are inferred from same-named upazilas (noted). চৌমুহনী and বসুরহাট (Noakhali) have no stated parent, so `upazila_en` is empty.
- Raw page texts have phone numbers and e-mails redacted.

## Licence

No licence stated; facts only. Attribution: জেলা প্রশাসন, চট্টগ্রাম বিভাগ — জাতীয় তথ্য বাতায়ন (<district>.gov.bd).
