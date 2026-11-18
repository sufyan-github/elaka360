# DGME medical and dental colleges — Mymensingh Division

- **Sources** (dgme.gov.bd `/pages/static-pages/`):
  - medical colleges with code, year and MBBS seats (updated 18 Dec 2025);
  - dental colleges and units (20 May 2024);
  - English names and websites of government colleges.
- **Method:** collected with `dgme_medical_colleges_raj_2026/fetch.py --division mymensingh`, accessed 2026-11-18. A row is kept when its Bangla name ends in a Mymensingh-Division district, or names one. Both Bangla spellings নেত্রকোনা and নেত্রকোণা are recognised. Dental units go in the parent college's `extra_json`.
- **Licence:** none stated.

## Result: 4 colleges (education.medical_college)

| | Government | Private | Armed forces | Total |
|---|---|---|---|---|
| MBBS colleges | 3 | 1 | 0 | 4 |
| Dental colleges | 0 | 0 | 0 | 0 |

| District | MBBS govt | MBBS private | Dental |
|---|---|---|---|
| Mymensingh | Mymensingh MC (code 14, 1962, 225 seats) | Community Based MC (108, 1995, 140; men and women) | Mymensingh MC dental unit (2012, 52 BDS seats) |
| Jamalpur | Jamalpur MC (code 34, 2014, 100 seats) | | |
| Netrokona | Netrokona MC (code 45, 2018, 50 seats) | | |
| Sherpur | none | none | none |

- **English names and websites:** from the government-college page: "Mymensingh Medical College" (http://mmc.gov.bd), "Jamalpur Medical College" and "Netrokona Medical College" (no website given). The private college has no English name in DGME's tables, so `name_en` stays empty; the English name in the table above is this report's translation.
- **Dental unit:** DGME lists "ময়মনসিংহ মেডিকেল কলেজ ডেন্টাল ইউনিট" without a district suffix. Its name matches the MBBS row exactly, so it is attached to college code 14 automatically; no hand match was needed.
- **Text search:** searching all three pages for the four district names (Bangla and English), "Bhaluka" and "Trishal" found no other Mymensingh-Division college.

## Gaps and doubts

- **Not in the tables:** addresses, phones, upazilas and coordinates. City colleges are `district_en = Mymensingh`, with no city corporation assigned.
- **Colleges, not hospitals:** link the college and hospital records; don't merge them.
