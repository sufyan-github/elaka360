# BD_RAILWAY_KHL_2026 — Bangladesh Railway (Khulna Division)

**Source:** railway.gov.bd (trust level 4), accessed 2026-11-18, via `bd_railway_raj_2026/fetch.py --division khulna`. Two pages were used:
- "গুরুত্বপূর্ন স্টেশনের টেলিফোন";
- Information Book 2023-2024, Table-4 (district-wise stations and route km; national table, kept as `raw/infobook_2023_24_table4.txt`).

## Collected
- **5 × `transport.railway_station`** from the important-stations list: কুষ্টিয়া (53058), কুষ্টিয়া কোর্ট (53065), যশোর (65019), বেনাপোল (75501), খুলনা (760691).
  - BTCL landlines as printed, without area codes.
  - The district, and the upazila for Benapole (Sharsha), were **added from the station's location; the source does not state them**.
- **16 facts:** stations and route km per district, FY 2023-24. Counts include block huts, halts and goods points.

| District | Stations | Route km |
|---|---|---|
| Bagerhat | 6 | 38.007 |
| Chuadanga | 10 | 56.600 |
| Jashore | 12 | 102.100 |
| Jhenaidah | 5 | 36.000 |
| Khulna | 8 | 51.050 |
| Kushtia | 10 | 79.520 |
| Narail | 2 | 29.500 |
| **Division (derived sum, 7 districts)** | **53** | **392.777** |

## Gaps
- **Satkhira, Meherpur and Magura** have no Table-4 row (no railway); no value is written.
- **Jhenaidah** is spelled "Jhenaidaha" in Table-4.
- **Not on the phone list:** Darshana, Chuadanga, Jhenaidah (Kotchandpur) and Bagerhat stations.
- There is no public station register, and eticket.railway.gov.bd is disallowed by robots.txt.
- **Licence:** none stated.
