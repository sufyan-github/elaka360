# FSCD_STATIONS_MYM_2026 — Fire Service & Civil Defence, Mymensingh Division

**Source:** fireservice.gov.bd (trust level 4), accessed 2026-11-18, via `fscd_stations_raj_2026/fetch.py --division mymensingh`. Used:
- the Mymensingh-division number list (PDF "ফায়ার সার্ভিস ও সিভিল ডিফেন্স, ময়মনসিংহ বিভাগ, ময়মনসিংহ", Word export 2026-08-11, 2 pages, 4 district tables; kept in raw/);
- the divisional control-room page;
- the national station/vehicle count page.

## Collected: 40 places, 14 facts
- **33 × `emergency.fire_station`:** Mymensingh 13, Netrokona 9, Jamalpur 7, Sherpur 4.
  - The upazila is set on 32 stations, inferred from the station name (flagged).
  - The district-town stations (ময়মনসিংহ, জামালপুর, শেরপুর, নেত্রকোনা) get the Sadar upazila.
- **6 × `government`:** FSCD office posts with their numbers: the Deputy Director, Assistant Director and Deputy Assistant Director in Mymensingh; the Assistant Director in Jamalpur; the Deputy Assistant Directors in Sherpur and Netrokona.
- **1 × `emergency`:** Mymensingh divisional control room: 02996671446, 01730-002353, 01968-881119.
- **Facts:**
  - stations per district (4);
  - the division's class counts from the national page: special 0, A 6, B 17, B land-cum-river 0, C 10, river 0, total 33;
  - pumps 148, ambulances 12, vehicles and pumps 383 (summary dated 20 Oct 2024; the "মঃসিংহ" column).

## Data quality
- **Names** were transcribed from the rendered pages (the text layer has broken Bangla glyphs). Numbers come from the text layer, as printed (11 digits without hyphen); all 39 PDF numbers were found in the text layer.
- **Station count:** the list has 33 stations, the same as the national page reports for the division.
- **Shared number:** মুক্তাগাছা and কৃষিবিশ্ববিদ্যালয় ফায়ার স্টেশন are both printed with 01901024225. Both are kept as printed and noted; the second row's id has a district suffix.
- **No upazila:** কৃষিবিশ্ববিদ্যালয় ফায়ার স্টেশন (the agricultural-university area).
- **Mymensingh table:** it skips serial 14 (13 is followed by 15, নান্দাইল); noted on that row.
- **Not in the list:** no Nokla (Sherpur) station.
- **Office-post numbers outside the FSCD 01901 series:** 01980-271354 (Deputy Director), 01819-848030 (Assistant Director, Mymensingh), 01718-092909 (Deputy Assistant Director, Netrokona). Kept as published by FSCD for the office post, as in Khulna. 01730-002353 (Deputy Assistant Director, Mymensingh) is also the divisional control-room number.
- No addresses or coordinates are published.

## Licence
None stated → `null`.
