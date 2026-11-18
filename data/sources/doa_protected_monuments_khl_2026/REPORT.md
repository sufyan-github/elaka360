# DoA protected monuments — Khulna Division

- **Source:** archaeology.gov.bd "খুলনা বিভাগের সংরক্ষিত পুরাকীর্তি" (/pages/static-pages/6922df45933eb65569e20fab). It links one PDF per district for all 10 districts; the PDFs and their text extractions are in `raw/`. Collected with `doa_protected_monuments_raj_2026/fetch.py --division khulna`, accessed 2026-11-18. Trust level 4.
- **Licence:** none stated.

## Result: 105 monuments, 10 facts

| District | Monuments (page count = rows parsed) | List published |
|---|---|---|
| Jhenaidah | 21 | 31-08-2024 |
| Bagerhat | 20 | 10-08-2026 |
| Narail | 16 | 31-08-2024 |
| Satkhira | 14 | 31-08-2024 |
| Jashore | 11 | 31-08-2024 |
| Kushtia | 10 | 25-06-2026 |
| Khulna | 7 | 31-08-2024 |
| Magura | 3 | 31-08-2024 |
| Chuadanga | 2 | 31-08-2024 |
| Meherpur | 1 | 31-08-2024 |

- **Categories:** tourism.historical 77, tourism.archaeological 25, religious.mazar 3.
- **Coordinates:** 97 rows. Values are converted from the published DMS values (one row is in decimal degrees) and checked against the HDX COD-AB Khulna polygons (`hdx_cod_ab_bgd_khulna`).
- **Upazila:** set on all 105 rows, from the location text. The booklet spellings মহাম্মদপুর, হরিনাকুন্ড and শৈলকূপা are recognised.
- **`extra_json`:** gazette reference as published (gazette, date, part/page, notification number), construction date phrase, coordinates as printed, serial, list date. Descriptions are not copied.

## Rows read from the rendered page

- **Khulna-07:** the text layer is broken. The name was read from the page: "কালি মন্দরের ধ্বংসাবশেষের ঢিবি" (spelling as printed).
- **Bagerhat-20:** the text layer is broken. Name, location, coordinates and gazette were read from the page: "কালিবাড়ি ও শিববাড়ি", কচুয়া গ্রামঃ মঘিয়া, gazette 09 জুলাই 2026.
- **Conversion fixes, checked against the pages:**
  - Narail-09 "ফয়জুল্লাহ (রহ.) এর": the segment was left unconverted because of "(in.)".
  - Khulna-04 location "রাড়ুলী": the u-kar was printed as an en dash.
  - Jashore-06 "(Page- 17)" in the 1975 list reference.

## Coordinates not used

- **Bagerhat-19 (ছিলিয়াখানা/অস্ত্রাগার প্রত্নঢিবি):** the published point (22.394, 89.4539) falls in Khulna/Dacope, not Bagerhat. Kept in extra_json.
- **Bagerhat-20:** printed "২২°৬৬'৭২.২০" উ. ৮৯°৮৭'২৫.২" পূ." — minutes and seconds above 59.
- **Jhenaidah-06 (মনোহর দীঘি ঢিবি):** latitude 26.365 is outside the division (source typo).
- **No coordinate in source:** Satkhira-11, Narail-13, Kushtia-10, Magura-01, Bagerhat-16.
- **Identical coordinates (flagged):** Jashore-03/04 (Sagardari) and Narail-10/11 (Raigram).

## Gaps and doubts

- **Magura-01:** the gazette text runs into description words in the text layer (kept as parsed in `gazette_reference_as_published`).
- **Bagerhat-19:** listed as Bagerhat Sadar although its point is in Dacope. Check on the ground.
