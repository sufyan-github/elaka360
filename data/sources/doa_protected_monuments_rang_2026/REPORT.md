# Department of Archaeology protected monuments — Rangpur Division

- **Source:** archaeology.gov.bd/pages/static-pages/6922dca5933eb65569e1169f ("রংপুর বিভাগ", one PDF per district; DoA states 59 monuments, updated to 13-07-2025).
- **Method:** collected with `doa_protected_monuments_raj_2026/fetch.py --division rangpur`, accessed 2026-11-17. `raw/` holds the 8 PDFs and their text (3.4 MB).
- **Text:** the PDFs are typed in Bijoy/SutonnyMJ. The text was converted to Unicode and spot-checked against the rendered pages. Descriptions are not copied.
- **Licence:** none stated.

## Counts: 59 rows (= DoA's stated total)

| District | Monuments |
|---|---|
| Dinajpur | 17 |
| Rangpur | 11 |
| Panchagarh | 9 |
| Thakurgaon | 7 |
| Kurigram | 6 |
| Nilphamari | 5 |
| Lalmonirhat | 2 |
| Gaibandha | 2 |

- The lists were published 31-08-2024 (Thakurgaon 13-07-2025).
- By category: tourism.historical 47, tourism.archaeological 10, religious.mazar 2.
- The upazila is set on all 59, from the location column. 19 rows have a construction-date phrase.
- `facts.csv`: 8 district counts.

## Coordinates: 48 of 59

- **Missing in the source (10):** Dinajpur-13, -16, -17; Lalmonirhat-02; Gaibandha-01; Thakurgaon-05, -06, -07; Rangpur-03, -08.
- **Blanked (1):** Kurigram-06, whose printed latitude 24°51' lies outside the division.
- **Flagged "check" by the HDX COD-AB QA:**
  - Nilphamari-05 (Nilphamari Govt High School): listed in Jaldhaka, but the point is in Nilphamari Sadar.
  - Thakurgaon-03: listed in Ranisankail, but the point is in Thakurgaon Sadar.
- Rangpur-10 and Rangpur-11 have almost the same point.
- Kurigram-02 is given in decimal degrees.

## Text fixes

- Bijoy conversion slips were corrected after checking the page images: সর্দারপাড়া (Kurigram-01), চোর চক্রবর্তী ঢিবি (Dinajpur-14), মুন্সিবাড়ি (Kurigram-04).
- The Thakurgaon PDF's header line ("নাম") is skipped instead of being glued to the last row of the previous page.
