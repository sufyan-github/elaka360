# DGME medical and dental colleges — Barishal Division

- **Sources** (dgme.gov.bd `/pages/static-pages/`):
  - medical colleges with code, year and MBBS seats (updated 18 Dec 2025);
  - dental colleges and units (20 May 2024);
  - English names and websites of government colleges.
- **Method:** collected with `dgme_medical_colleges_raj_2026/fetch.py --division barishal`, accessed 2026-11-18. A row is kept when its Bangla name ends in a Barishal-Division district, or names one. Dental units go in the parent college's `extra_json`.
- **Licence:** none stated.

## Result: 3 colleges (education.medical_college)

| | Government | Private | Armed forces | Total |
|---|---|---|---|---|
| MBBS colleges | 2 | 1 | 0 | 3 |
| Dental colleges | 0 | 0 | 0 | 0 |

| District | MBBS govt | MBBS private | Dental |
|---|---|---|---|
| Barishal | Sher-e-Bangla MC (code 16, 1968, 225 seats) | South Apollo MC (code 163, 2021, 50 seats) | Sher-e-Bangla MC dental unit (2012, 52 BDS seats) |
| Patuakhali | Patuakhali MC (code 36, 2014, 100 seats) | | |
| Bhola, Pirojpur, Jhalokathi, Barguna | none | none | none |

- **English names and websites:** from the government-college page: "Sher-E-Bangla Medical College, Barisal" (sbmc.gov.bd) and "Patuakhali Medical College" (pkmc.gov.bd). The private college has no English name in DGME's tables, so it stays empty.
- **Dental unit:** DGME lists "শের-ই-বাংলা মেডিকেল কলেজ ডেন্টাল ইউনিট" without a district suffix; it is attached to the parent college by exact name.
- A text search of all three pages for the six district names (Bangla and English) found no other Barishal-Division college.

## Gaps and doubts

- **Not in the tables:** addresses, phones, upazilas and coordinates. City colleges are `district_en = Barishal`, with no city corporation assigned.
- **Colleges, not hospitals:** link the college and hospital records; don't merge them.
