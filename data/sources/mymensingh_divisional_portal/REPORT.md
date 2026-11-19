# Mymensingh Divisional Commissioner portal (mymensinghdiv.gov.bd)

- **Collector:** `rajshahi_divisional_portal/fetch.py --division mymensingh`. Host verified by its title "হোম | ময়মনসিংহ বিভাগ".
- **Pages** from the menu (`raw/pages.csv`, texts in `raw/`):
  - এক নজরে ময়মনসিংহ বিভাগ (2025-08-06);
  - জেলার তালিকা → "ময়মনসিংহ বিভাগের জেলা ও উপজেলাসমূহ" (2018-09-09);
  - উপজেলার তালিকা (2018-09-09);
  - ইউনিয়নের তালিকা → "ময়মনসিংহ বিভাগের সকল উপজেলার ইউনিয়নের নামের তালিকা" (2022-05-10).
  - Upazila and union portal addresses come from the national registry, which this portal does not link (`raw/national_portal_list.csv` keeps the 35 registry upazilas).
- **areas.csv (391):**
  - **4 districts.** `code` is the list serial (`MYMDIV_LIST_SERIAL`). Website is the DC portal; the page links it as www.<district>.gov.bd.
  - **35 upazilas** from a table "ক্রমিক নং | জেলার নাম | মোট উপজেলা | উপজেলার নাম", one row per district with a comma list. "হালুয়াঘাটও ধোবাউড়া" ('ও' written onto the name) is read as two upazilas (noted). All 35 websites are from the registry.
  - **352 unions** from eight tables under the headings "X জেলা" and "X জেলার ইউনিয়ন পরিষদের নামসমূহ":
    - a summary table "উপজেলার নাম | পৌরসভার নাম | ইউনিয়ন সংখ্যা" (the pourashava column is not read as unions);
    - a table "উপজেলার নাম | ইউনিয়ন পরিষদের নাম" with comma lists.
    - Websites are from the registry where the name matches (344).
- **facts.csv (107):**
  - এক নজরে table of districts: area, upazilas, unions and population per district, and the total row. Division: 10,552 km², 35 upazilas, 351 unions, population 11,447,583 (no year).
  - The district rows:

| District | Area km² | Upazilas | Unions | Population |
|---|---|---|---|---|
| Mymensingh | 4,363.48 | 13 | 146 | 5,313,163 |
| Jamalpur | 2,031 | 7 | 67 | 2,384,810 (printed "২৩,৮৪৮১০", DOUBT) |
| Netrokona | 2,794 | 10 | 86 | 2,207,000 |
| Sherpur | 1,363.76 | 5 | 52 | 1,542,610 |

  - এক নজরে also gives 5,114 mouzas.
  - Upazila list: stated upazilas per district (13/7/10/5); 35 listed.
  - Union page:
    - stated unions per upazila (35, from the summary tables);
    - district totals (মোট: 13/145, 10/86, 7/68, 5/52);
    - "মোট ইউনিয়ন সংখ্যা: ৩৫১ টি";
    - listed counts and unions per upazila.

## Conflicts and caveats

- **Listed 352 against stated 351.** Sherpur Sadar lists 15 against its stated 14: বেতমারী-ঘুঘুরাকান্দি is printed "বেতমারি, ঘুঘুরাকান্দি" and is read as two items, as printed.
- **Dhobaura** prints a truncated "দক্ষিণ" (the DC list has দক্ষিণ মাইজপাড়া); kept as printed, with no website.
- **No website** (no registry match): দক্ষিণ, রসুলপুর, চরবৈতাগৈর, বীরবৈতাগের, তেতুলিয়া, বেতমারি, ঘুঘুরাকান্দি, রাজনগর.
- **Misprints read with DOUBT:** "ময়নসিংহ সদর" (summary table), "পূ্র্বধলা".
- **Two pages disagree:** this portal's এক নজরে gives Mymensingh 146 and Jamalpur 67 unions; its union page gives 145 and 68.
- **Against the DC portals:**
  - Mymensingh 145 here against 127 on mymensingh.gov.bd. Haluaghat (12), Gouripur (10), Phulpur (10) and Tarakanda (10, with গালাগাঁও) are complete here.
  - The other districts match per upazila.
- **Population years:** the district table prints no year. Prefer BBS 2022.
- A "জেলা প্রশাসক" menu page lists people and is not used.

## Licence

No licence stated; facts only. Attribution: Office of the Divisional Commissioner, Mymensingh (mymensinghdiv.gov.bd); upazila and union portal addresses from the Bangladesh National Portal (bangladesh.gov.bd/views/union-list).
