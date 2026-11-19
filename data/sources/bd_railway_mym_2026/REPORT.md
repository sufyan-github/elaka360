# BD_RAILWAY_MYM_2026 — Bangladesh Railway (Mymensingh Division)

**Source:** railway.gov.bd (trust level 4), accessed 2026-11-18, via `bd_railway_raj_2026/fetch.py --division mymensingh`. Two pages were used:
- "গুরুত্বপূর্ন স্টেশনের টেলিফোন" (kept as `raw/railway_important_station_phones.txt`; unchanged since the Sylhet run);
- Information Book 2023-2024, Table-4 (district-wise stations and route km; national table, kept as `raw/infobook_2023_24_table4.txt`; parsed from the PDF text).

## Collected
- **3 × `transport.railway_station`** from the important-stations list: নেত্রকোনা (02996651475), ময়মনসিংহ (55700; 55667; 55757), জামালপুর (63040).
  - BTCL landlines as printed. Mymensingh and Jamalpur are printed without the area code; Netrokona's is printed in the 11-digit form with the area code, although the row note says "without area code".
  - The district was **added from the station's location; the source does not state it**. No upazila is set (district-town stations).
- **8 facts:** stations and route km per district, FY 2023-24. Counts include block huts, halts and goods points.

| District | Stations | Route km |
|---|---|---|
| Jamalpur | 21 | 107.000 |
| Mymensingh | 20 | 146.000 |
| Netrokona | 17 | 66.000 |
| **Division (derived sum, 3 districts)** | **58** | **319.0** |

## Gaps
- **Sherpur** has no railway: no Table-4 row and no station on the phone list.
- There is no public station register, and eticket.railway.gov.bd is disallowed by robots.txt.
- **Licence:** none stated.
