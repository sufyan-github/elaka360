# FSCD_STATIONS_DHK_2026 — Fire Service & Civil Defence, Dhaka Division

**Source:** Fire Service and Civil Defence Directorate (fireservice.gov.bd), trust level 4. Accessed 2026-11-17. Collected with `fscd_stations_raj_2026/fetch.py --division dhaka`.

- "সকল ফায়ার স্টেশনের নম্বর" page → Dhaka-division PDF (`raw/fscd_dhaka_division_numbers.pdf`, Word export created 2026-08-11, 5 pages, 13 district tables), "নতুন যোগাযোগ নাম্বার" for every station and office.
- Control-room page ("ঢাকা নিয়ন্ত্রণ কক্ষ") and "চালুকৃত ফায়ার স্টেশন ও গাড়ী/পাম্পের সংখ্যা" (Dhaka row/column).

## What was collected (151 rows)

| | Rows |
|---|---|
| `emergency.fire_station` | 130 |
| `government` (FSCD office posts: DD/AD/DAD with official numbers) | 20 |
| `emergency` (Dhaka control room) | 1 |

Stations per district:

| District | Stations |
|---|---|
| Dhaka | 29 |
| Kishoreganj | 14 |
| Tangail | 13 |
| Narayanganj | 12 |
| Gazipur | 11 |
| Faridpur | 9 |
| Munshiganj | 7 |
| Narsingdi | 7 |
| Manikganj | 7 |
| Shariatpur | 6 |
| Rajbari | 5 |
| Madaripur | 5 |
| Gopalganj | 5 |

`facts.csv` (23 rows):
- stations listed per district;
- division station counts by class, from an undated page: special 7, A 37, B 55, B land-cum-river 4, C 18, river 5, total 126;
- Dhaka column, summary dated 20 Oct 2024: FSCD pumps 421, ambulances 53, all vehicles and pumps 1374.

## Coverage
- **Phone: 151/151**, all official numbers.
  - The control room has +02-223355555, 01730-336699 and 01713-038181-2.
  - All PDF numbers were re-read from the live text layer, including the Secretariat landline; none changed.
  - The PDF prints the mobile numbers without hyphens; they are stored as 01901-0xxxxx.
- **Not published:** coordinates, addresses and per-station class. `name_en` is empty (Bangla only).
- **Upazila:** `upazila_en` is set for the 76 stations named after their upazila (inferred from the name). Dhaka-city stations, district-town stations and stations such as Kanchpur, Tongi, Madhabdi, Elenga and Teknerhat are not set.

## Data-quality issues
- The PDF's Bangla text layer is broken, so names were **transcribed by hand from the rendered pages**.
- **Kalyanpur fire station is listed twice** (serials 32 and 35, same number 01901-020766); it is kept once.
- **Same number for two posts:** 01901-020705 is printed for Deputy-Assistant Director Zone-2 (Dhaka) and Zone-2 (Narayanganj). Both are kept (second id `fscd-dhk-01901020705-narayanganj`).
- **Numbers outside the FSCD 01901 series, kept because the official list prints them:**
  - Secretariat station: landline only (02-9515555, old 7-digit Dhaka format).
  - Kashimpur mini station: 01755-630094.
- **Temporary station:** Hazrat Shahjalal International Airport station is listed as temporary (অস্থায়ী).
- **Serial quirks:** Gazipur starts at 1, 3, 4, 5, 5; Narsingdi skips 5.
- **Station count mismatch:** the PDF lists 130 stations, the undated national counts page says 126.

## Licence
No licence stated → `license: null`.
