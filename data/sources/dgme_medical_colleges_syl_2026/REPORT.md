# DGME medical and dental colleges — Sylhet Division

- **Sources** (dgme.gov.bd `/pages/static-pages/`):
  - medical colleges with code, year and MBBS seats (updated 18 Dec 2025);
  - dental colleges and units (20 May 2024);
  - English names and websites of government colleges.
- **Method:** collected with `dgme_medical_colleges_raj_2026/fetch.py --division sylhet`, accessed 2026-11-18. A row is kept when its Bangla name ends in a Sylhet-Division district, or names one. Dental units go in the parent college's `extra_json`.
- **Licence:** none stated.

## Result: 8 colleges (education.medical_college)

| | Government | Private | Armed forces | Total |
|---|---|---|---|---|
| MBBS colleges | 3 | 4 | 0 | 7 |
| Dental colleges | 0 | 1 | 0 | 1 |

| District | MBBS govt | MBBS private | Dental |
|---|---|---|---|
| Sylhet | Sylhet MAG Osmani MC (code 15, 1962, 225 seats) | Jalalabad Ragib-Rabeya MC (109, 1996, 130), North East MC (111, 1998, 125), Sylhet Women's MC (128, 2006, 100; women), Park View MC (156, 2014, 82) | MAG Osmani dental unit (2012, 52 BDS seats); Sylhet Central Dental College (private, 2015, 40 BDS seats) |
| Habiganj | Habiganj MC (code 41, 2017, 50 seats) | | |
| Sunamganj | Sunamganj MC (code 47, 2020, 75 seats) | | |
| Moulvibazar | none | none | none |

- **English names and websites:** from the government-college page: "Sylhet MAG Osmani Medical College" (magosmanimedical.com), "Habiganj Medical College" (no website given) and "Sunamganj Medical College" (bbmcs.edu.bd, as printed). Private colleges have no English name in DGME's tables, so `name_en` stays empty; the English names in the table above are this report's translations.
- **Dental unit:** DGME lists "এমএজি ওসমানী মেডিকেল কলেজ ডেন্টাল ইউনিট" without a district suffix, spelt differently from the MBBS row ("সিলেট এম.এ.জি. ওসমানী মেডিকেল কলেজ, সিলেট"). It is attached to college code 15 by hand (`UNIT_PARENT_BY_HAND`), and the row's notes say so.
- **Text search:** searching all three pages for the four district names (Bangla and English), "Osmani" and "Ragib" found no other Sylhet-Division college. Moulvibazar has no college on DGME's lists.

## Gaps and doubts

- **Not in the tables:** addresses, phones, upazilas and coordinates. City colleges are `district_en = Sylhet`, with no city corporation assigned.
- **Sunamganj website:** the government-college page links bbmcs.edu.bd, a domain that appears to carry the college's earlier name; kept as published.
- **Colleges, not hospitals:** link the college and hospital records; don't merge them.
