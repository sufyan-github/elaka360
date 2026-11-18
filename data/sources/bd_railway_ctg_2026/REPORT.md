# BD_RAILWAY_CTG_2026 — Bangladesh Railway (Chattogram Division)

**Source:** railway.gov.bd (trust level 4), accessed 2026-11-17, via `bd_railway_raj_2026/fetch.py --division chattogram`. Two pages were used:
- "গুরুত্বপূর্ন স্টেশনের টেলিফোন";
- Information Book 2023-2024, Table-4 (district-wise stations and route km; national table, kept as `raw/infobook_2023_24_table4.txt`).

## Collected
- **7 × `transport.railway_station`** from the important-stations list: ব্রাহ্মণবাড়ীয়া (085152006), আশুগঞ্জ (085174221), আখাউড়া (085156012), কুমিল্লা (76358; 76353; 76028), চাঁদপুর (63255), ফেনী (74875), চট্টগ্রাম (0241360037; 0241360038; 0241360039).
  - BTCL landlines as printed; Cumilla, Chandpur and Feni have no area code.
  - The district, and the upazila for Ashuganj and Akhaura, were **added from the station's location; the source does not state them**.
- **16 facts:** stations and route km per district, FY 2023-24. Counts include block huts, halts and goods points.

| District | Stations | Route km |
|---|---|---|
| Brahmanbaria | 16 | 66.600 |
| Chandpur | 10 | 52.050 |
| Chattogram | 49 | 176.830 |
| Cox's Bazar | 6 | 46.490 |
| Cumilla | 18 | 101.230 |
| Feni | 13 | 96.560 |
| Noakhali | 7 | 47.310 |
| **Division (derived sum, 7 districts)** | **119** | **587.07** |

## Gaps
- **Lakshmipur, Rangamati, Khagrachhari and Bandarban** have no Table-4 row (no railway); no value is written.
- **Cox's Bazar** is spelled "Coxbazar" in Table-4.
- **Blank rows:** rows 12 and 17–19 of the phone page are empty.
- There is no public station register, and eticket.railway.gov.bd is disallowed by robots.txt.
- **Licence:** none stated.
