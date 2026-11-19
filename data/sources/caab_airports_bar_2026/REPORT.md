# CAAB_AIRPORTS_BAR_2026 — airports in Barishal Division (CAAB)

**Source:** caab.gov.bd (Bangla menu) and new.caab.gov.bd (airport page, "All airports" overview, contacts page). Trust level 4. Accessed 2026-11-18, via `caab_airports_raj_2026/fetch.py --division barishal`. Page text is kept in `raw/barisal.txt`.

## Collected (1 × `transport.airport`)
| Airport | District | ICAO/IATA | Coordinates | Status (CAAB overview) | Office contact |
|---|---|---|---|---|---|
| Barishal Airport (বরিশাল বিমানবন্দর) | Barishal | VGBR / BZL | 22.798942, 90.301236 | Domestic, operational | +880 2 478833552 (office); +880 1894909700 (cell); apmbarisal@caab.gov.bd |

- **Coordinates:** converted from the degree/minute/second values printed on the page ("22 o 47'56.19"N", "090 o 18'04.45"E").
- **`extra_json`:**
  - TWR 128.10/129.30 MHz and NDB 368 kHz;
  - the Airport Manager's fax (+880 2 55061662) and the control-tower line (+880 2 55061673);
  - the overview status.
- **Contacts:** only the Airport Manager's office block. On this page the cell number is followed by "Fax :", not "e-mail", so the collector reads it up to "Fax" (Barishal only). Airline-office numbers, the VIP-lounge line and the airport police number are not collected.
- **Contacts page:** it lists +880 4327 73362 for the Barishal Airport Manager (twice). This number is not on the airport page; it is flagged in notes and kept in `extra_json.numbers_on_contacts_page`.
- **No other airport in the division:** the CAAB overview ("TWELVE DOMESTIC AIRPORTS …") names no other airport in Barishal Division.
- **No upazila:** none set. The page names only "Barishal".

## Licence
None stated → `null`.
