# FSCD_STATIONS_RANG_2026 — Fire Service & Civil Defence, Rangpur Division

**Source:** Fire Service and Civil Defence Directorate (fireservice.gov.bd), trust level 4. Accessed 2026-11-17. Collected with `fscd_stations_raj_2026/fetch.py --division rangpur`.

- "সকল ফায়ার স্টেশনের নম্বর" page → Rangpur-division PDF (`raw/fscd_rangpur_division_numbers.pdf`, Word export created 2026-08-11), "নতুন যোগাযোগ নাম্বার" for every station and office.
- Control-room page (Rangpur divisional control room) and "চালুকৃত ফায়ার স্টেশন ও গাড়ী/পাম্পের সংখ্যা" (Rangpur row/column).
- No divisional-portal cross-check: fireservice.rangpur.gov.bd has one page per Rangpur-district station but no number list like Rajshahi's.

## What was collected (72 rows)
| | Rangpur District | Division total |
|---|---|---|
| `emergency.fire_station` | 9 | 60 |
| `government` (FSCD office posts: DD/AD/DAD with official numbers) | 3 | 11 |
| `emergency` (Rangpur divisional control room) | 1 | 1 |

Stations per district:

| District | Stations |
|---|---|
| Dinajpur | 13 |
| Rangpur | 9 |
| Kurigram | 8 |
| Nilphamari | 8 |
| Gaibandha | 7 |
| Lalmonirhat | 5 |
| Thakurgaon | 5 |
| Panchagarh | 5 |

`facts.csv` (18 rows):
- stations listed per district;
- division station counts by class, from an undated page: special 0, A 6, B 40, B land-cum-river 0, C 13, river 0, total 59;
- Rangpur column, summary dated 20 Oct 2024: FSCD pumps 183, ambulances 19, all vehicles and pumps 499.

## Coverage
- **Phone: 72/72**, all official numbers. The control room has 02589962222, 02589962226, 02589962228 and 01732-707172. All 71 PDF numbers were re-read from the live text layer (Bangla digits converted); none changed.
- **Not published:** coordinates, addresses and per-station class. `name_en` is empty (Bangla only).
- **Upazila:** `upazila_en` is set for the 46 stations named after their upazila (inferred from the name). It is not set for the 6 district-town stations, nor for Haragachh, Kortimari, Uttara EPZ, Chilahati, Setabganj and Hili.

## Data-quality issues
- The PDF's Bangla text layer is broken, so names were **transcribed by hand from the rendered pages**.
- The PDF prints the **same number 01901-023337 for Gaibandha and Kurigram fire stations**; both kept (second id `fscd-rang-01901023337-kurigram`).
- "কর্তিমারী ফায়ার স্টেশন" (Kurigram): conjunct hard to read on the rendered page (may be printed "কত্তিমারী"); upazila not inferred.
- Kurigram's Phulbari station is listed with 01723-976767, outside the FSCD 01901 series; kept because the official list prints it.
- Station count mismatch: the PDF lists 60 stations, the undated national counts page says 59.
- Not duplicated: national hotline 102.

## Licence
No licence stated → `license: null`.
