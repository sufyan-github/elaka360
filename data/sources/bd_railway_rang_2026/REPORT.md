# BD_RAILWAY_RANG_2026 — Bangladesh Railway (Rangpur Division)

**Source:** railway.gov.bd (trust level 4), accessed 2026-11-17, via `bd_railway_raj_2026/fetch.py --division rangpur`. Two pages were used:
- "গুরুত্বপূর্ন স্টেশনের টেলিফোন";
- Information Book 2023-2024, Table-4 (district-wise stations and route km; national table, kept as `raw/infobook_2023_24_table4.txt`).

## Collected
- **7 × `transport.railway_station`** from the important-stations list: বোনারপাড়া, গাইবান্ধা (Gaibandha), রংপুর, কুড়িগ্রাম, ঠাকুরগাঁও, নীলফামারী, সৈয়দপুর (Nilphamari).
  - BTCL landlines are printed without area code (Saidpur only "2104").
  - The district, and the upazila for Bonarpara → Saghata and Saidpur → Saidpur, were **added from the station's location; the source does not state them**.
  - Dinajpur, Parbatipur, Lalmonirhat and Panchagarh are not on the phone list.
- **18 facts:** stations and route km per district, FY 2023-24. Counts include block huts, halts and goods points.

| District | Stations | Route km |
|---|---|---|
| Dinajpur | 24 | 143.800 |
| Gaibandha | 14 | 80.950 |
| Kurigram | 8 | 42.500 |
| Lalmonirhat | 15 | 114.000 |
| Nilphamari | 9 | 65.300 |
| Panchagarh | 3 | 18.320 |
| Rangpur | 9 | 63.800 |
| Thakurgaon | 6 | 47.180 |
| **Division (derived sum)** | **88** | **575.85** |

## Gaps
- There is no public station register, and eticket.railway.gov.bd is disallowed by robots.txt.
- **Licence:** none stated.
