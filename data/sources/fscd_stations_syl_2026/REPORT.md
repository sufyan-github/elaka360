# FSCD_STATIONS_SYL_2026 — Fire Service & Civil Defence, Sylhet Division

**Source:** fireservice.gov.bd (trust level 4), accessed 2026-11-18, via `fscd_stations_raj_2026/fetch.py --division sylhet`. Used:
- the Sylhet-division number list (PDF "ফায়ার সার্ভিস ও সিভিল ডিফেন্স, সিলেট বিভাগ, সিলেট", Word export 2026-08-11, 2 pages, 4 district tables; kept in raw/);
- the divisional control-room page;
- the national station/vehicle count page.

## Collected: 45 places, 14 facts
- **38 × `emergency.fire_station`:** Sylhet 12, Sunamganj 11, Habiganj 8, Moulvibazar 7.
  - The upazila is set on 36 stations, inferred from the station name (flagged).
  - The district-town stations (সিলেট, সুনামগঞ্জ, মৌলভীবাজার, হবিগঞ্জ) get the Sadar upazila.
- **6 × `government`:** FSCD office posts with their numbers: the Deputy Director, Sylhet; the Assistant Director for greater Sylhet; and four Deputy Assistant Directors (Sylhet, Sunamganj, Moulvibazar, Habiganj).
- **1 × `emergency`:** Sylhet divisional control room: 02996643339, 02996643356, 02996643458, 02996643394, 02996643396, 01730-336644.
- **Facts:**
  - stations per district (4);
  - the division's class counts from the national page: special 0, A 2, B 27, B land-cum-river 1, C 8, river 0, total 38;
  - pumps 124, ambulances 12, vehicles and pumps 324 (summary dated 20 Oct 2024; the Sylhet column was checked against the page header).

## Data quality
- **Names** were transcribed from the rendered pages (the text layer has broken Bangla glyphs). Numbers come from the text layer, as printed (mixed Bangla/ASCII digits); all 44 are in the FSCD 01901 series and all were found in the text layer.
- **Station count:** the list has 38 stations, the same as the national page reports for the division.
- **No upazila:** সিলেট দক্ষিণ (Sylhet South) and সিলেট সেনানিবাস (Sylhet Cantonment).
- **লাখাই স্থলকাম-নদী ফায়ার স্টেশন:** a land-cum-river station. `extra_json.station_type` says so. The collector now tells land-cum-river from river stations, for Sylhet only.
- **Sunamganj table:** it skips serial 10 (09 is followed by 11, ধর্মপাশা); noted on that row.
- **Printed as published:**
  - "সহকারী পরিচালক, বৃহওর সিলেট জেলা" ("বৃহওর" for বৃহত্তর);
  - commas in the office posts ("উপসহকারী পরিচালক,সিলেট");
  - two Habiganj numbers printed without a hyphen (01901023692, 01901023696).
- No addresses or coordinates are published.

## Licence
None stated → `null`.
