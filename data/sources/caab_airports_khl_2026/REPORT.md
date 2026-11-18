# CAAB_AIRPORTS_KHL_2026 — airports in Khulna Division (CAAB)

**Source:** caab.gov.bd (Bangla menu) and new.caab.gov.bd (airport page, "All airports" overview, contacts page). Trust level 4. Accessed 2026-11-18, via `caab_airports_raj_2026/fetch.py --division khulna`. Page text is kept in `raw/jessore.txt`.

## Collected (2 × `transport.airport`)
| Airport | District | ICAO/IATA | Coordinates | Status (CAAB overview) | Office contact |
|---|---|---|---|---|---|
| Jashore Airport (যশোর বিমানবন্দর) | Jashore | VGJR / JSR | 23.18375, 89.160892 | Domestic, operational | +880 421 64033; 01894909600; apmjessore@caab.gov.bd |
| Khan Jahan Ali Airport | Bagerhat | — | — | Under construction | — |

- **Coordinates:** converted from the degree/minute/second values printed on the Jashore page ("23 o 11' 01.50" N", "089 o 09' 39.21" E").
- **`extra_json`:** TWR 123.2/123.9 MHz, DVOR/DME "JSR, Freq, 113 MHz / 1164 MHz", VHF frequencies, and the tower phone +880 421 65032.
- **Contacts:** only the Airport Manager's office block. On the Jashore page its numbers are printed without a "Phone:" label (flagged). Airline-office numbers and the separate control-tower lines are not collected. The contacts page confirms +880 421 64033 and apmjessore@caab.gov.bd.
- **Khan Jahan Ali Airport:** only named in the overview ("UNDER CONSTRUCTION Khan Jahan Ali Airport, Bagerhat"). CAAB publishes no page, codes, coordinates or contact for it.
- **No upazila:** none set.

## Licence
None stated → `null`.
