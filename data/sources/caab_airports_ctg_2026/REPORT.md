# CAAB_AIRPORTS_CTG_2026 — airports in Chattogram Division (CAAB)

**Source:** caab.gov.bd (Bangla menu) and new.caab.gov.bd (airport pages, "All airports" overview, contacts page). Trust level 4. Accessed 2026-11-17, via `caab_airports_raj_2026/fetch.py --division chattogram`. Page text is kept in `raw/` (chittagong.txt, coxsbazar.txt, comilla.txt).

## Collected (3 × `transport.airport`)
| Airport | District | ICAO/IATA | Coordinates | Status (CAAB overview) | Office contact |
|---|---|---|---|---|---|
| Shah Amanat International Airport (শাহ আমানত আন্তর্জাতিক বিমানবন্দর) | Chattogram | VGEG / CGP | 22.257022, 91.822208 | International | +880 2 41350100; dsaiactg@caab.gov.bd |
| Cox's Bazar Airport (কক্সবাজার বিমানবন্দর) | Cox's Bazar | VGCB / CXB | 21.451944, 91.963889 | Domestic, operational | 01894909300; +880-2333346980; apmcox@caab.gov.bd |
| Cumilla Airport (কুমিল্লা বিমানবন্দর) | Cumilla | VGCM / CLA | 23.436111, 91.188028 | Service not available | 08176119; apmcomilla@caab.gov.bd |

- **Coordinates:** converted from the aerodrome reference values printed on each page. Formats differ: DDMMSS for Shah Amanat, "21 o 27′07"N" for Cox's Bazar, a "GPS" line for Cumilla. TWR/VOR/DVOR/NDB frequencies are in `extra_json`.
- **Contacts:** only the Airport Director's or Manager's office block (phone, cell, e-mail). Airline-office and staff numbers are not collected.
- **Cumilla Airport** also has a CAAB page and is included. CAAB says only over-flying facilities (VOR, NDB) are available there.
- **No upazila:** none set (the airports are named after the city or district).

## Conflicts
- **Shah Amanat:** the airport page prints the e-mail with spaces ("dsaiactg@caa b . gov.bd"; read as dsaiactg@caab.gov.bd). The contacts page gives apmctg@caab.gov.bd. Both are recorded.
- **Cox's Bazar:** the page gives apmcox@caab.gov.bd; the contacts page gives dcox@caab.gov.bd. Both are recorded.
- **Other districts:** no other airport is listed in the division.

## Licence
None stated → `null`.
