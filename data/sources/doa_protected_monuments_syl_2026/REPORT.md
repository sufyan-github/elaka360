# DoA protected monuments — Sylhet Division

- **Source:** archaeology.gov.bd "সিলেট বিভাগের সংরক্ষিত পুরাকীর্তি" (/pages/static-pages/6922e035933eb65569e26000). It links one PDF per district for all 4 districts; the PDFs and their text extractions are in `raw/`. Collected with `doa_protected_monuments_raj_2026/fetch.py --division sylhet`, accessed 2026-11-18. Trust level 4.
- **Licence:** none stated.

## Result: 17 monuments, 4 facts

| District | Monuments (page count = rows parsed) | List published |
|---|---|---|
| Sylhet | 12 | 31-08-2024 |
| Habiganj | 2 | 31-08-2024 |
| Sunamganj | 2 | 31-08-2024 |
| Moulvibazar | 1 | 31-08-2024 |

- **Categories:**
  - religious.mazar 2: the Shahjalal and Shahporan dargahs.
  - tourism.archaeological 1: Bhatera Tila Mound.
  - tourism.historical 14: temples, mosques, five megalithic-tomb groups at Jaintiapur, Irabati Panthashala, Hawli/Awli Rajbari, Pailgaon Zamindar Bari, Bithangal Akhra.
- **Coordinates:** 16 rows, converted from the published DMS values. Sylhet-12 (গায়েবী দিঘীর প্রাচীন মসজিদ) has none; the cell shows "-".
- **Upazila:** set on all 17 rows, from the location text. The spelling "বিয়ানী বাজার" (with a space) is recognised.
- **Point-in-polygon QA:** ran against `hdx_cod_ab_bgd_sylhet`. Every point falls in its listed district and upazila. Sylhet-01 and Sylhet-03 fall in the Sylhet City Corporation polygon; they are listed as Sylhet Sadar.
- **`extra_json`:** gazette reference as published (gazette, date, part/page, notification number), construction date phrase, coordinates as printed, serial, list date. Descriptions are not copied.

## Conversion fixes, checked against the rendered pages
- **Bijoy "k^" (শ্ব):** the converter gives "শব". Fixed: "জৈন্তাশ্বর" (Sylhet-05, -08), "জৈন্তাশ্বও" (Sylhet-06, as printed) and "পার্শ্বে" (Sylhet-05, -08).
- **"সেপ্টেম্বর":** in the gazette dates of Sylhet-10 and -11; the converter gives "সেন্মেম্বর".
- **Photo column:** the "আলোকচিত্র" column (a "-" where there is no photo) is dropped.

## Gaps and doubts

- **Long names:** the five megalithic-tomb rows (Sylhet-05 to -09) print the whole cell as the name, including the location and stone counts (for example "… লম্বা পাথর 3টি ডিম্বাকৃতির 2টি"). They are kept as printed. Digits stay ASCII, as in the earlier divisions' names.
- **Assam Gazette (1921):** Sylhet-01, -02 and -04 cite the Assam Gazette. The reference and date are kept in `gazette_reference_as_published`; the `gazette` field is empty because that name is not in the collector's list.
- **Moulvibazar-01 (ভাটেরা টিলা মাউন্ড):** the notification date is printed "১৮.১১.১৯০" (cut off in the source); kept as printed.
- **Habiganj-02:** the gazette reference starts "গংস্কৃতি বিষয়ক মন্ত্রণালয়ের …" as printed (for সংস্কৃতি). The name "বিথঙ্গঁল বড় আখড়া" is kept as printed.
- **Spelling kept as printed:** "সম্মুখস্ত" (Sylhet-05).
