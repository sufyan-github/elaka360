# FSCD_STATIONS_BAR_2026 — Fire Service & Civil Defence, Barishal Division

**Source:** fireservice.gov.bd (trust level 4), accessed 2026-11-18, via `fscd_stations_raj_2026/fetch.py --division barishal`. Used:
- the Barishal-division number list (PDF "ফায়ার সার্ভিস ও সিভিল ডিফেন্স, বরিশাল বিভাগ, বরিশাল", Word export 2026-08-11, 2 pages, 6 district tables; kept in raw/);
- the divisional control-room page;
- the national station/vehicle count page.

## Collected: 50 places, 16 facts
- **42 × `emergency.fire_station`:** Barishal 11, Pirojpur 7, Bhola 7, Patuakhali 7, Barguna 6, Jhalokathi 4. The upazila is set on 38 stations named after their upazila or their district town (inferred from the name, flagged). For the district-town stations (পিরোজপুর, ঝালকাঠি, ভোলা, বরগুনা), the upazila is the Sadar upazila.
- **7 × `government`:** FSCD office posts (one Deputy Director, two Assistant Directors and four Deputy Assistant Directors) with their numbers.
- **1 × `emergency`:** Barishal divisional control room. Numbers: 01878001111, 01983886677, 02478832499, 02478832500, 02478830299, 02478832500-7. The page prints "01983886677 02478832499" with a single space; the collector now splits them.
- **Facts:**
  - stations per district (6);
  - the division's class counts from the national page: special 0, A 3, B 27, B land-cum-river 0, C 10, river 2, total 42;
  - pumps 111, ambulances 16, vehicles and pumps 337 (summary dated 20 Oct 2024).

## Data quality
- **Names** were transcribed from the rendered pages (the text layer has broken Bangla glyphs). Numbers come from the text layer, as printed; all are in the FSCD 01901 series.
- **Station count:** the list has 42 stations, the same as the national page reports for the division.
- **Patuakhali table:** the PDF heads it "পিরোজপুর জেলা" (a second Pirojpur heading). Its rows are Patuakhali's offices and stations, so they are `district_en = Patuakhali` (flagged on each row).
- **Barishal District posts:** "উপপরিচালক" and "সহকারী পরিচালক" are printed without a place name (flagged).
- **No upazila** for stations named after a locality or for river stations: বরিশাল দক্ষিন, বরিশাল নদী, পটুয়াখালি নদী, খেপুপাড়া.
- **জিয়ানগর ফায়ার স্টেশন:** printed with the upazila's former name Zianagar; `upazila_en = Indurkani` (flagged).
- **Printed as published:** "বানরিপাড়া ফায়ার স্টেশ" (sic), "বাখেরগঞ্জ", "মুলাদি", "পটুয়াখালি", "দক্ষিন".
- No addresses or coordinates are published.

## Licence
None stated → `null`.
