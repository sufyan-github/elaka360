# FSCD_STATIONS_KHL_2026 — Fire Service & Civil Defence, Khulna Division

**Source:** fireservice.gov.bd (trust level 4), accessed 2026-11-18, via `fscd_stations_raj_2026/fetch.py --division khulna`. Used:
- the Khulna-division number list (PDF "ফায়ার সার্ভিস ও সিভিল ডিফেন্স, খুলনা বিভাগ, খুলনা", Word export 2026-08-11, 3 pages, 10 district tables; kept in raw/);
- the divisional control-room page;
- the national station/vehicle count page.

## Collected: 81 places, 20 facts
- **64 × `emergency.fire_station`:** Khulna 13, Bagerhat 10, Jashore 9, Satkhira 7, Jhenaidah 6, Kushtia 5, Magura 4, Chuadanga 4, Narail 3, Meherpur 3. The upazila is set on 50 stations named after their upazila or a district Sadar (inferred from the name, flagged).
- **16 × `government`:** FSCD office posts (Deputy, Assistant and Deputy Assistant Directors; in Khulna also "ফোরম্যান" and "ও সি কন্ট্রোল") with their numbers.
- **1 × `emergency`:** Khulna divisional control room. Numbers: 024777-00333 to 024777-00337, 01733-062209.
- **Facts:**
  - stations per district (10);
  - the division's class counts from the national page: special 0, A 8, B 45, B land-cum-river 1, C 8, river 1, total 63;
  - pumps 187, ambulances 25, vehicles and pumps 514 (summary dated 20 Oct 2024).

## Data quality
- **Names** were transcribed from the rendered pages (the text layer has broken Bangla glyphs). Numbers come from the text layer, as printed.
- **Noapara (নওয়াপাড়া) fire station:** the number is printed with 9 digits ("০১৯১২-৬৮২৮"). The phone is empty; the printed value is in `extra_json.phone_as_printed`.
- **Outside the FSCD 01901 series:**
  - স্থলকাম নদী ফায়ার স্টেশন (01301-022748, possibly a misprint);
  - Manirampur (01740-322834);
  - the Khulna Foreman (01920-659967) and OC Control (01717-934439) posts.
- **01901-022852** is printed for both the Harinakunda and Kaliganj (Jhenaidah) stations.
- **Khulna's "নদী ফায়ার স্টেশন" and "স্থলকাম নদী ফায়ার স্টেশন"** have no place name.
- **"ডুমুরিয়া বটিয়াঘাটা ফায়ার স্টেশন"** names two upazilas, and a separate বটিয়াঘাটা station follows; no upazila is set.
- **Station count:** the list has 64 stations, while the national page reports 63 for the division.
- **No upazila** for stations named after a locality or a metropolitan thana: Khulna Sadar, Khalishpur, Tutpara, Daulatpur, Khan Jahan Ali, the two river stations, Mongla EPZ, Senanibas (Jashore), Noapara, Benapole, Darshana, Bamundi.
- **Printed as published:** "দৌলাতপুর", "খুকসা", "কোটচাদপুর", "লোহাগাড়া".
- No addresses or coordinates are published.

## Licence
None stated → `null`.
