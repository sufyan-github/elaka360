# DoA protected monuments — Barishal Division

- **Source:** archaeology.gov.bd "বরিশাল বিভাগের সংরক্ষিত পুরাকীর্তি" (/pages/static-pages/6922e128933eb65569e2a90f). It links one PDF per district for all 6 districts; the PDFs and their text extractions are in `raw/`. Collected with `doa_protected_monuments_raj_2026/fetch.py --division barishal`, accessed 2026-11-18. Trust level 4.
- **Licence:** none stated.

## Result: 28 monuments, 6 facts

| District | Monuments (page count = rows parsed) | List published |
|---|---|---|
| Barishal | 10 | 31-08-2024 |
| Patuakhali | 7 | 31-08-2024 |
| Pirojpur | 6 | 13-07-2025 |
| Jhalokathi | 3 | 31-08-2024 |
| Bhola | 1 | 10-08-2026 |
| Barguna | 1 | 31-08-2024 |

- **Categories:** tourism.historical 28 (mosques, two maths, a tomb, an old bridge, zamindar houses, the Barishal Collectorate building, Sher-e-Bangla's birth house and rest house).
- **Coordinates:** 26 rows, converted from the published DMS values.
- **Upazila:** set on all 28 rows, from the location text. The spellings দুমকী, ভাণ্ডারিয়া and মেহেন্দীগঞ্জ are recognised.
- **`extra_json`:** gazette reference as published (gazette, date, part/page, notification number), construction date phrase, coordinates as printed, serial, list date. Descriptions are not copied.

## Rows read from the rendered page

- **Bhola-01:** the Unicode text layer is broken. Name, location and gazette were read from the page: "নিগামন মসজিদ", উপজেলাঃ ভোলা সদর ইউনিয়নঃ দক্ষিণ দিঘলদী গ্রামঃ দক্ষিণ দিঘলদী, বাংলাদেশ গেজেট ০৯ জুলাই ২০২৬. The coordinates parse from the text layer as printed.
- **Conversion fixes, checked against the pages:**
  - "সেপ্টেম্বর" in three gazette dates (Jhalokathi-01, Barishal-03, Barishal-09); the converter gives "সেন্মেম্বর".
  - Patuakhali-07 name "আমিরুল্লাহ মুন্সিবাড়ি জামে মসজিদ".
  - Patuakhali-06: the 1975 list reference "Protected Monuments and Mounds in Bangladesh (District-wise) 1975 by Department of Archaeology and Museums (Page- 22)"; its small words fall into the description column of the text layer.
- **Coordinates parsed as printed, label irregular:**
  - Barishal-06: the longitude label is printed "পূ" without its dot.
  - Pirojpur-04: printed ".৯০°০৪'৫৫.৬" পূ ." with a stray dot and a spaced label.

## Coordinates not used

- **Pirojpur-06 (রাজপাশা সরদার বাড়ি প্রাচীন মসজিদ):** printed "২২°৪৬'২.৯৫৮" উ. ৯০°০'২৪৮৫৯" পূ.". The seconds value of the longitude is malformed. Kept in extra_json.
- **No coordinate in source:** Pirojpur-05 (শেখ ভেলাই মসজিদ; the cell shows "-").

## Gaps and doubts

- **No polygon QA:** the HDX COD-AB Barishal extract (`hdx_cod_ab_bgd_barishal`) was not in the repository when this ran, so the point-in-polygon check was skipped. Rerun the collector once it exists. A rough check against the seed's district polygons put all points in their listed district except Pirojpur-03/04.
- **Pirojpur-03 and Pirojpur-04 (Bhandaria):** they have identical published coordinates (22°29'18.4" N, 90°04'55.6" E; flagged). The point falls just inside Jhalokathi in the seed's district polygons, which are coarse. Check on the ground.
- **Barishal-06:** the gazette reference reads "নয়াাদিল্লীর …" as printed.
- **Gazette dates in Bijoy text:** these read "আগষ্ট" where the page shows "আগস্ট". Kept as converted.
