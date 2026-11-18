# DGME medical and dental colleges — Chattogram Division

- **Sources** (dgme.gov.bd `/pages/static-pages/`):
  - medical colleges with code, year and MBBS seats (updated 18 Dec 2025);
  - dental colleges and units (20 May 2024);
  - English names and websites of government colleges.
- **Method:** collected with `dgme_medical_colleges_raj_2026/fetch.py --division chattogram`, accessed 2026-11-17. A row is kept when its Bangla name ends in a Chattogram-Division district, or names one. Dental units go in the parent college's `extra_json`.
- **Licence:** none stated.

## Result: 20 colleges (education.medical_college)

| | Government | Private | Armed forces | Total |
|---|---|---|---|---|
| MBBS colleges | 6 | 10 | 3 | 19 |
| Dental colleges | 0 | 1 | 0 | 1 |

| District | MBBS govt | MBBS private | Armed forces | Dental |
|---|---|---|---|---|
| Chattogram | 1 (Chattogram MC, with dental unit) | 6 (Institute of Applied Health Sciences, Chattogram International MC, Chattogram Ma-O-Shishu Hospital MC (with dental unit), BGC Trust MC, Marine City MC, Southern MC) | Army MC, Navy MC | Chattogram International Dental College (private) |
| Cumilla | 1 | 3 (Eastern, Mainamoti, Central) | Army MC | |
| Chandpur | 1 | | | |
| Cox's Bazar | 1 | | | |
| Noakhali | 1 | | | |
| Rangamati | 1 | | | |
| Brahmanbaria | | 1 (Brahmanbaria MC) | | |
| Feni, Lakshmipur, Khagrachhari, Bandarban | none | none | none | none |

- **Dental units:** Chattogram MC (1989, 60 BDS seats) and Chattogram Ma-O-Shishu Hospital MC (2023, 20 seats), matched by the parent's exact name.
- **English names and websites:** found for all 6 government colleges (each district has one government MBBS college), with websites for 5. DGME spells "Chattagram Medical College" (website cmc.gov.bd). Noakhali MC has no website on the page.
- **Armed forces:** Army MC Chattogram, Army MC Cumilla and Navy MC Chattogram are listed in the private table without a college code. They are marked `armed_forces` (Navy MC: 2025, 50 seats).

## Gaps and doubts

- Chattogram International MC and Chattogram Ma-O-Shishu Hospital MC have no district suffix; the district comes from "চট্টগ্রাম" in the name.
- **Not in the tables:** addresses, phones, upazilas and coordinates. City colleges are `district_en = Chattogram`, with no city corporation assigned.
- **Colleges, not hospitals:** link the college and hospital records; don't merge them.
