# DGME medical and dental colleges — Khulna Division

- **Sources** (dgme.gov.bd `/pages/static-pages/`):
  - medical colleges with code, year and MBBS seats (updated 18 Dec 2025);
  - dental colleges and units (20 May 2024);
  - English names and websites of government colleges.
- **Method:** collected with `dgme_medical_colleges_raj_2026/fetch.py --division khulna`, accessed 2026-11-18. A row is kept when its Bangla name ends in a Khulna-Division district, or names one. Dental units go in the parent college's `extra_json`.
- **Licence:** none stated.

## Result: 11 colleges (education.medical_college)

| | Government | Private | Armed forces | Total |
|---|---|---|---|---|
| MBBS colleges | 5 | 4 | 1 | 10 |
| Dental colleges | 1 | 0 | 0 | 1 |

| District | MBBS govt | MBBS private | Armed forces | Dental |
|---|---|---|---|---|
| Khulna | Khulna MC (1992, 200 seats) | Gazi MC, Ad-din Akij MC, Khulna City MC | | Khulna Dental College (government) |
| Jashore | Jashore MC (2010, 100) | Ad-din Sakina Women's MC (women only) | Army MC Jashore (2014, 60) | |
| Kushtia | Kushtia MC (2011, 100) | | | |
| Satkhira | Satkhira MC (2011, 100) | | | |
| Magura | Magura MC (2018, 50) | | | |
| Bagerhat, Narail, Jhenaidah, Chuadanga, Meherpur | none | none | none | none |

- **English names and websites:** the government-college page lists only Khulna Medical College (kmc.gov.bd), Magura Medical College (maguramc.edu.bd) and Satkhira Medical College (no website) for this division. Jashore and Kushtia MCs have no English row there, so their English names are empty.
- **Dental units:** none in this division.
- **Armed forces:** Army MC Jashore is listed in the private table without a college code; it is marked `armed_forces`.

## Gaps and doubts

- **Khulna Dental College:** its row prints "অনুমোদন প্রাপ্ত" across the year and seat cells. No year or BDS seats are given; `approval_status` holds the first word as parsed.
- **Not in the tables:** addresses, phones, upazilas and coordinates. City colleges are `district_en = Khulna`, with no city corporation assigned.
- **Colleges, not hospitals:** link the college and hospital records; don't merge them.
