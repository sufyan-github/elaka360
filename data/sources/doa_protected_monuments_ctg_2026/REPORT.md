# Department of Archaeology protected monuments — Chattogram Division

- **Source:** archaeology.gov.bd/pages/static-pages/6922deb6933eb65569e1cce1 ("চট্টগ্রাম বিভাগের সংরক্ষিত পুরাকীর্তি", one PDF per district). DoA states 64 monuments "আগস্ট ২০২৬ পর্যন্ত".
- **Method:** collected with `doa_protected_monuments_raj_2026/fetch.py --division chattogram`, accessed 2026-11-17. `raw/` holds the 7 PDFs and their text (2.3 MB).
- **Text:** the PDFs are mostly Bijoy/SutonnyMJ text (converted to Unicode). The Chattogram PDF has one row with a broken Unicode text layer (row 6) and one row on a page without the table header (row 8); both were read from the rendered pages. Photo captions are dropped. Descriptions are not copied.
- **Licence:** none stated.

## Counts: 64 rows (= DoA's stated total)

| District | Monuments | Published |
|---|---|---|
| Cumilla | 35 | 31-08-2024 |
| Chattogram | 8 | 31-08-2026 |
| Feni | 6 | 31-08-2024 |
| Brahmanbaria | 6 | 31-08-2024 |
| Chandpur | 6 | 31-08-2024 |
| Noakhali | 2 | 31-08-2024 |
| Lakshmipur | 1 | 31-08-2024 |
| Rangamati, Cox's Bazar, Khagrachhari, Bandarban | 0 ("সংরক্ষিত পুরাকীর্তি নেই"; no PDF) | |

- **By category:** tourism.historical 48, tourism.archaeological 15, religious.mazar 1.
- **Upazila:** set on all 64 rows from the location column. Chattogram-07 and -08 (কোতয়ালী) hold the CMP thana Kotwali, with a note. Cumilla: Sadar Dakshin 24, Adarsha Sadar 4, Barura 3, Debidwar, Burichang, Laksam, Manoharganj. "কুমিল্লা সদর" (Cumilla-35) is read as Adarsha Sadar (the former Comilla Sadar).
- **Construction date:** 25 rows have a construction-date phrase.
- **`facts.csv`:** 11 district counts (4 of them 0).

## Coordinates: 51 of 64

- **Missing in the source (12):** Cumilla 11 (-04, -08, -14, -17 to -22, -30, -31) and Chattogram-03.
- **Not parseable (1):** Cumilla-35 prints "23.48.26.25. Dt 91.20.72.78.97 c~." (kept in extra_json).
- **Parser fix:** several Cumilla rows print the latitude label "D." one column to the right, next to the gazette text. It is re-attached to the coordinate, otherwise 7 points would have been lost.
- **Chattogram-06 (হামিদিয়া মসজিদ প্রকাশ):** the page labels the latitude "দ." and the longitude "উ."; the values (22°31'46.40", 91°42'04.49") are read as north/east (noted).
- **Flagged "check" (HDX COD-AB polygons):**
  - Cumilla-02, -03, -06, -07, -12, -13, -16, -23, -24: listed in Sadar Dakshin, but the points fall in Adarsha Sadar (Mainamati/Kotbari ridge, cantonment).
  - Noakhali-01 (Bajra Shahi Masjid): listed in Begumganj, but the point falls in Sonaimuri.

## Text fixes (all checked on the rendered pages)

- **Chattogram-06:** name হামিদিয়া মসজিদ প্রকাশ (হাম্মাদিয়া); location গ্রাম- মসজিদিয়া ইউনিয়ন- ৭ নং কুমিরা উপজেলা- সীতাকুন্ড; gazette বাংলাদেশ গেজেট ২২ জানুয়ারি, ২০১৫ (১ম খন্ড পৃষ্টা নং-১০৬).
- **Chattogram-08:** location কোতয়ালী; coordinates and gazette (২৭ ডিসেম্বর, ২০১৮) read from the page.
- **Bijoy slips:** কচুয়া (Chandpur-04, split over two lines), সেপ্টেম্বর (Chattogram-07 gazette), "District-wise" in the 1975 reference.
- **Header residue:** the repeated header word "নাম" (Bijoy "bvg") on every Cumilla page is skipped.
