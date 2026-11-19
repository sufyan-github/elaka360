# BD_RAILWAY_SYL_2026 — Bangladesh Railway (Sylhet Division)

**Source:** railway.gov.bd (trust level 4), accessed 2026-11-18, via `bd_railway_raj_2026/fetch.py --division sylhet`. Two pages were used:
- "গুরুত্বপূর্ন স্টেশনের টেলিফোন" (kept as `raw/railway_important_station_phones.txt`; unchanged since the Barishal run);
- Information Book 2023-2024, Table-4 (district-wise stations and route km; national table, kept as `raw/infobook_2023_24_table4.txt`; parsed from the PDF text).

## Collected
- **5 × `transport.railway_station`** from the important-stations list: শায়েস্তাগঞ্জ (56646), শ্রীমঙ্গল (71350), কুলাউড়া (56004), সিলেট (716061; 717036; 716051; 713990), হবিগঞ্জ (52260).
  - BTCL landlines as printed, without area codes.
  - The district, and the upazila for Shayestaganj, Sreemangal and Kulaura, were **added from the station's location; the source does not state them**. Sylhet and Habiganj stations get no upazila.
- **10 facts:** stations and route km per district, FY 2023-24. Counts include block huts, halts and goods points.

| District | Stations | Route km |
|---|---|---|
| Habiganj | 14 | 89.100 |
| Moulvibazar | 11 | 116.700 |
| Sunamganj | 2 | 13.300 |
| Sylhet | 6 | 49.400 |
| **Division (derived sum, 4 districts)** | **33** | **268.5** |

## Gaps
- **Phone list:** no Sunamganj station is on it.
- There is no public station register, and eticket.railway.gov.bd is disallowed by robots.txt.
- **Licence:** none stated.
