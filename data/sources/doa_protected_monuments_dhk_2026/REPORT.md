# Department of Archaeology protected monuments — Dhaka Division

- **Source:** archaeology.gov.bd/pages/static-pages/6922dde7933eb65569e16ff2 ("ঢাকা বিভাগ", one PDF per district). DoA states 111 monuments "আগস্ট ২০২৬ পর্যন্ত".
- **Method:** collected with `doa_protected_monuments_raj_2026/fetch.py --division dhaka`, accessed 2026-11-17. `raw/` holds the 13 PDFs and their text (7.6 MB).
- **Text:** the PDFs mix Bijoy/SutonnyMJ text (converted to Unicode) with Unicode text whose text layer is partly broken. Rows with slips were checked against the rendered pages and fixed. Photo captions (column "আলোকচিত্র") are dropped. Descriptions are not copied.
- **Licence:** none stated.

## Counts: 111 rows (= DoA's stated total)

| District | Monuments |
|---|---|
| Dhaka | 35 |
| Narayanganj | 18 |
| Kishoreganj | 14 |
| Munshiganj | 9 |
| Narsingdi | 6 |
| Shariatpur | 6 |
| Gopalganj | 6 |
| Gazipur | 4 |
| Manikganj | 4 |
| Madaripur | 3 |
| Tangail | 2 |
| Rajbari | 2 |
| Faridpur | 2 |

- **Publication dates:** lists published 28/31-08-2024; Narsingdi and Munshiganj 31-08-2026; Rajbari 10-08-2026.
- **By category:** tourism.historical 105, tourism.archaeological 4, religious.mazar 2.
- **Upazila:** set on 82 rows from the location column.
  - 25 Dhaka-city rows hold the DMP thana instead (Lalbagh, Kotwali, Sutrapur, Ramna, Mohammadpur, Chawkbazar, Dhanmondi, New Market, Badda), with a note.
  - 4 rows have none: dhaka-08 আজিমপুর, dhaka-14 আরমানিটোলা, dhaka-25 নারিন্দা, dhaka-34 "ঢাকা দক্ষিণ সিটি".
- **Construction date:** 39 rows have a construction-date phrase.
- **`facts.csv`:** 13 district counts.

## Coordinates: 69 of 111

- **Missing in the source (37):** Dhaka 11, Shariatpur 6, Narayanganj 5, Gopalganj 3, and 2 or 1 in other districts. Munshiganj-07 is counted here, although it prints a mislabelled, out-of-range pair (দ./উ., 77.5").
- **Blanked (5):**
  - Narsingdi-06, Munshiganj-09 and Rajbari-02: seconds ≥ 60.
  - Dhaka-35: printed "23.39'29.99' / 900 8'30.91'", which cannot be parsed.
  - Rajbari-01: the point falls in Faridpur/Bhanga, and it is identical to Faridpur-01's coordinates.
- **Flagged "check":**
  - Narayanganj-12, -13 and -14 (listed in Bandar; the points fall in the Narayanganj City Corporation polygon).
  - Kishoreganj-03: the same point as -01, in Kishoreganj Sadar rather than Pakundia.
  - Munshiganj-05: the point is in Munshiganj Sadar.
  - Munshiganj-08: the same point as -06, in Sreenagar.
  - Dhaka-33: the same point as -32.
- **Gopalganj-06:** its minute mark is a Bijoy 'Õ', read as '.

## Text fixes (all checked on the rendered pages)

- **Bijoy slips:** মুন্সিগঞ্জ, কর্তৃক, বাড্ডা, নাটেশ্বর, ঢাকেশ্বরী.
- **Broken Unicode rows replaced by the visible text:** Narsingdi-06 (বায়তুন নূর পাড়াতলী জামে মসজিদ; গ্রাম- পাড়াতলী উপজেলা- রায়পুর), Munshiganj-07 (শ্যামসিদ্ধির মঠ and its location), Rajbari-01 (জোড়বাংলা মন্দির; উপজেলাঃ বালিয়াকান্দি …), Rajbari-02 (দোলমঞ্চ ও স্নানমঞ্চ; উপজেলাঃ রাজবাড়ী সদর …), Manikganj-04 (কমপ্লেক্স), Narayanganj-18 (সেতু).
- **Parser changes:** the Munshiganj PDF indents its serial numbers, so it is re-parsed. Header continuation lines and the group heading "লালবাগ দুর্গ:" are skipped.
- **Location variants used for upazila matching:** শরিয়তপুর সদর, কালীহাতি, মকসুদপুর.
