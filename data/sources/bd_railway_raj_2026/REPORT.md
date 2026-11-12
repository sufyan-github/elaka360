# BD_RAILWAY_RAJ_2026 — Bangladesh Railway (Rajshahi Division)

**Source:** railway.gov.bd (trust level 4), accessed 2026-11-12:
"গুরুত্বপূর্ন স্টেশনের টেলিফোন" (BTCL phones of important stations) and the annual **Information Book 2023-2024** (Table-4
"District-wise station & route kilometers", PDF page 46; text extract in `raw/infobook_2023_24_table4.txt`).

## What exists / what does not
- **No public station register** on railway.gov.bd (no per-station list with district, station code or class). The timetable
  and fare files list stops of individual trains only; the "স্টেশন… রির্জাভেশন চার্জ" PDF is a scanned notice, not a station list.
- `eticket.railway.gov.bd/robots.txt` = `Disallow: /` → its station list was **not** used (blocked by robots).

## Collected
- 7 × `transport.railway_station` (the important-stations list rows inside the division): রাজশাহী, রাজশাহী কোর্ট (Rajshahi),
  চাঁপাই নবাবগঞ্জ, রোহনপুর (Chapainawabganj), নাটোর, জয়পুরহাট, বগুড়া. Phone 7/7 (BTCL landline, printed without area code).
  District (and Rohanpur's upazila Gomastapur) **added from the station's location — not stated by the source** (flagged in notes).
  No coordinates, codes or classes.
- facts (18): stations and route-km per district, FY 2023-24 — Bogura 20 / 84.850, Chapainawabganj 8 / 50.000, Joypurhat 7 / 45.500,
  Naogaon 5 / 18.100, Natore 11 / 77.070, Pabna 21 / 145.640, Rajshahi 11 / 70.000, Sirajganj 8 / 47.475; division sum 91 stations /
  538.635 km (derived). Counts include block huts, halts and goods booking points.

So Rajshahi District has 11 stations officially but only 2 named here (+ Arani in DISTRICT_PORTALS_TRANSPORT_RAJ_2026).

## Data quality
- Phone list has no area codes (e.g. Rajshahi "774043, 776040"); not added.
- Ishwardi, Santahar, Abdulpur, Pabna, Sirajganj Bazar are not on the important-stations phone list.
- Not duplicated: national hotline 131 (already in `HOTLINES`).

## Licence
None stated → `null`. The 1.5 MB Information Book PDF is not committed; `fetch.py` re-downloads it (needs `pdftotext`, else uses the
transcribed Table-4 values in the script).
