# BD_RAILWAY_DHK_2026 — Bangladesh Railway (Dhaka Division)

**Source:** railway.gov.bd (trust level 4), accessed 2026-11-17, via `bd_railway_raj_2026/fetch.py --division dhaka`. Two pages were used:
- "গুরুত্বপূর্ন স্টেশনের টেলিফোন";
- Information Book 2023-2024, Table-4 (district-wise stations and route km; national table, kept as `raw/infobook_2023_24_table4.txt`).

## Collected
- **9 × `transport.railway_station`** from the important-stations list: ঢাকা, তেজগাঁও, ঢাকা ক্যান্টনমেন্ট, ঢাকা বিমান বন্দর (Dhaka), টঙ্গী (Gazipur), নরসিংদী, ভৈরব বাজার, কিশোরগঞ্জ (Kishoreganj) and রাজবাড়ী.
  - BTCL landlines: the Dhaka-area numbers carry 02; Kishoreganj (55245) and Rajbari (65223) are printed without an area code.
  - The district, and the upazila for Tongi → Gazipur Sadar and Bhairab Bazar → Bhairab, were **added from the station's location; the source does not state them**.
- **26 facts:** stations and route km per district, FY 2023-24. Counts include block huts, halts and goods points.

| District | Stations | Route km |
|---|---|---|
| Dhaka | 7 | 45.560 |
| Faridpur | 16 | 109.690 |
| Gazipur | 9 | 99.580 |
| Gopalganj | 10 | 79.150 |
| Kishoreganj | 12 | 63.100 |
| Madaripur | 1 | 15.420 |
| Munshiganj | 3 | 27.260 |
| Narayanganj | 4 | 8.500 |
| Narsingdi | 14 | 39.000 |
| Rajbari | 15 | 89.900 |
| Shariatpur | 1 | 9.260 |
| Tangail | 8 | 87.525 |
| **Division (derived sum, 12 districts)** | **100** | **673.945** |

## Gaps
- **Manikganj** has no Table-4 row (no railway); no value is written.
- **Kishoreganj** is spelled "Kishorganj" in Table-4.
- There is no public station register, and eticket.railway.gov.bd is disallowed by robots.txt.
- **Licence:** none stated.
