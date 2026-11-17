# CAAB_AIRPORTS_RANG_2026 — airports in Rangpur Division (CAAB)

**Source:** caab.gov.bd (Bangla menu) and new.caab.gov.bd (airport page, "All airports" overview, contacts page). Trust level 4. Accessed 2026-11-17, via `caab_airports_raj_2026/fetch.py --division rangpur`.

## Collected (2 × `transport.airport`)
| Airport | District | ICAO / IATA | Coordinates | Contact |
|---|---|---|---|---|
| সৈয়দপুর বিমানবন্দর / Saidpur Airport | Nilphamari (Saidpur) | VGSD / SPD | 25.760375, 88.758469 | +880552672384 (Airport Manager), 01894909400, apmsaidpur@caab.gov.bd |
| Thakurgaon Airport | Thakurgaon | — | — | — |

- **Saidpur:** domestic, operational. Its DVOR/DME is in `extra_json`; airline, APBN and security numbers are not collected.
- **Thakurgaon:** "Service not available". It appears only in CAAB's overview, with no page, codes or contact.
- **Lalmonirhat:** the airfield is not listed by CAAB.

## Data quality
- Saidpur's latitude is printed with spaces ("254537 . 35N") and is read as 254537.35N (noted).
- Saidpur's upazila is taken from the airport name.

## Licence
None stated → `null`.
