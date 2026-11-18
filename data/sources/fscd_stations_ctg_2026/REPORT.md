# FSCD_STATIONS_CTG_2026 — Fire Service & Civil Defence, Chattogram Division

**Source:** fireservice.gov.bd (trust level 4), accessed 2026-11-17, via `fscd_stations_raj_2026/fetch.py --division chattogram`. Used:
- the Chattogram-division number list (PDF "ফায়ার সার্ভিস ও সিভিল ডিফেন্স, চট্টগ্রাম বিভাগ, চট্টগ্রাম", Word export 2026-08-11, 5 pages, 14 tables: Chattogram district zones 1–4 and 10 other districts; kept in raw/);
- the divisional control-room page;
- the national station/vehicle count page.

## Collected: 118 places, 21 facts
- **101 × `emergency.fire_station`:** Chattogram 25, Cumilla 13, Chandpur 10, Brahmanbaria 9, Noakhali 9, Cox's Bazar 8, Bandarban 7, Khagrachhari 6, Feni 5, Lakshmipur 5, Rangamati 4. The upazila is set on 73 stations named after their upazila (inferred from the name, flagged).
- **16 × `government`:** FSCD office posts (Deputy, Assistant and Deputy Assistant Directors) with their official numbers.
- **1 × `emergency`:** Chattogram divisional control room. Numbers: 02333311153, 02333311152, 02333331150, 01730-336666.
- **Facts:**
  - stations per district (11);
  - the division's class counts from the national page: special 1, A 26, B 57, B land-cum-river 2, C 16, river 2, total 104;
  - pumps 378, ambulances 37, vehicles and pumps 1,029 (summary dated 20 Oct 2024).

## Data quality
- **Names** were transcribed from the rendered pages (the text layer has broken Bangla glyphs). Numbers come from the text layer, as printed.
- **12-digit numbers (6 rows):** উপপরিচালক চট্টগ্রাম, উপসহকারী পরিচালক চট্টগ্রাম-১, আগ্রাবাদ, উপসহকারী পরিচালক ব্রাহ্মণবাড়িয়া, উপসহকারী পরিচালক চাঁদপুর, সেনবাগ. The phone field is empty; the printed value is in `extra_json.phone_as_printed`.
- **Kaptai fire station** is listed under Chattogram Zone-3 and under Rangamati with the same number. It is kept once, under Rangamati.
- **01901-021508** is printed for both the Chattogram Zone-3 and the Khagrachhari Deputy Assistant Directors.
- **Naikhongchhari station:** 01897-878797 is outside the 01901 series, and its name's text layer is in Bijoy encoding.
- **Printed as published:**
  - "কুমিল্লা ইপিজেড ফায়ার" and "দৌলতগঞ্জবাজার ফায়ার" (no "স্টেশন");
  - "আলীকদমফায়ারস্টেশন" (no spaces);
  - Chandpur's "নদী ফায়ার স্টেশন" (no place name);
  - "উপসকারী পরিচালক, লক্ষীপুর";
  - the Lakshmipur table repeats serial 2.
- **Station count:** the list has 101 distinct stations, while the national page reports 104 for the division.
- **No upazila** for stations named after a locality or district (e.g. Agrabad, Bandar, CEPZ, KEPZ, Nandankanan, Lamarbazar, Chandanpura, Kalurghat, Kumira, Bayezid, Bariarhat, Cumilla EPZ, Daulatganj Bazar, Chauyara Bazar, Chandpur North/South, Matlab, Maijdee, Chowmuhani).
- No addresses or coordinates are published.

## Licence
None stated → `null`.
