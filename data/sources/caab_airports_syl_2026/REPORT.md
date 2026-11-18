# CAAB_AIRPORTS_SYL_2026 — airports in Sylhet Division (CAAB)

**Source:** caab.gov.bd (Bangla menu) and new.caab.gov.bd (airport page, "All airports" overview, contacts page). Trust level 4. Accessed 2026-11-18, via `caab_airports_raj_2026/fetch.py --division sylhet`. Page text is kept in `raw/osmani.txt`.

## Collected (2 × `transport.airport`)
| Airport | District | ICAO/IATA | Coordinates | Status (CAAB overview) | Office contact |
|---|---|---|---|---|---|
| Osmani International Airport (ওসমানী আন্তর্জাতিক বিমানবন্দর) | Sylhet | VGSY / ZYL | 24.961342, 91.871636 | International | 880 821 714243 (office); 01715018027 (Airport Manager mobile); apmsylhet@caab.gov.bd |
| Shamshernagar Airport | Moulvibazar (added, see below) | — | — | Needs prior approval for air operation | — |

- **Osmani coordinates:** converted from the DDMMSS values on the page ("245740.83N", "0915217.89E"). The point falls in the Sylhet Sadar upazila polygon of `hdx_cod_ab_bgd_sylhet`; `upazila_en` is left empty because the page does not name one.
- **Osmani `extra_json`:** TWR 122.9 / 122.5 MHz, VOR 116.4 MHz, NDB 372 KHz, PABX +880 821 725391 to 94, overview status. The contacts page gives the same office number (+880 821 714243) and e-mail.
- **Contacts:** only the Airport Manager's office block ("Phone: 880 821 714243 (Off) Mobile-01715018027 email : …"; the office number is printed without "+"). Airline-office numbers are not collected.
- **Collector change:** for Sylhet, the generic "Cell:" reader matched Regent Airways' cell number further down the page. Sylhet therefore reads only the "Mobile-" number after "(Off)".
- **Shamshernagar Airport:** CAAB has no page for it. The overview names it only as "Shamshernagar Airport (STOL)" under "B. Needs prior approval for air operation", without a district. `district_en = Moulvibazar` is added from the airfield's location (Shamshernagar, Kamalganj upazila) and flagged in notes. No upazila, codes, coordinates or contact.
- **No other airfield in the division** is named by CAAB.

## Licence
None stated → `null`.
