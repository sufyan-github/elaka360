# DISTRICT_PORTALS_TRANSPORT_DHK_2026 — terminals/stands/stations named on Dhaka Division portals

**Source** (trust level 4, accessed 2026-11-17):
- "যোগাযোগ ব্যবস্থা" pages of the district portals dhaka, narsingdi, gazipur, shariatpur, narayanganj, tangail, kishoreganj, manikganj, munshiganj, rajbari `.gov.bd`, and of the Dhaka upazila portals savar, dhamrai, keraniganj, nawabganj, dohar.
- Dhaka South City Corporation "বাস টার্মিনাল" page and Dhaka North City Corporation "লোকেশন ও আয়তন" (ward areas).

**No portal publishes a bus-terminal register.** Rows are places the pages name explicitly; each is re-checked against the live page text by `fetch.py`. `raw/` keeps, per page that gave a row, only the lines carrying the matched phrases (some pages list bus-counter staff with mobiles; those are not kept).

**fetch.py:** `dhaka` entry in `SITES` (pages, phrase entries, manifest); raw handling above applies to divisions after Rangpur only.

## Collected (20)
| District | Category | Names |
|---|---|---|
| Dhaka | bus_terminal (3) | সায়েদাবাদ আন্ত-জেলা বাস টার্মিনাল (DSCC), গাবতলী বাস টার্মিনাল (DNCC ward 9), মহাখালী বাসস্ট্যান্ড (Tangail page) |
| Dhaka | bus_stop (2) | গুলিস্থান বাস স্ট্যান্ড, নবাবগঞ্জ বাস স্ট্যান্ড (Nawabganj upazila; `upazila_en` Nawabganj) |
| Dhaka | railway_station (2) | কমলাপুর রেল স্টেশন, গেন্ডারিয়া রেলস্টেশন |
| Dhaka | launch_ghat / airport | সদরঘাট (Munshiganj page), শাহজালাল আন্তর্জাতিক বিমানবন্দর (Dhaka page) |
| Narayanganj | railway_station (4) | পাগলা, ফতুল্লা, চাষাড়া, নারায়ণগঞ্জ (+ "রেলস্টেশন"; from the Dhaka–Narayanganj train timetable) |
| Tangail | bus_terminal | টাঙ্গাইল নতুন বাসস্ট্যান্ড |
| Kishoreganj | bus_terminal | বত্রিশ বাসস্ট্যান্ড |
| Manikganj | bus_terminal / launch_ghat | মানিকগঞ্জ বাসস্ট্যান্ড, পাটুরিয়াঘাট, আরিচাঘাট |
| Shariatpur | bus_terminal | শরীয়তপুর বাস স্ট্যান্ড |
| Munshiganj | launch_ghat | কাঠপট্টি ঘাট |

No facts (no page gives a terminal count).

**Gaps:**
- No coordinates, addresses or contacts. `upazila_en` is set only for Nawabganj bus stand.
- Gazipur, Rajbari and the Savar, Dhamrai, Keraniganj and Dohar pages name no terminal or station (routes, bus companies, owners' mobiles, UNO contacts). Madaripur's "যোগাযোগ" link is a DC contact card; Gopalganj and Faridpur have no transport page.

## Doubts
- Composed names: the Narayanganj line stations ("<stop> রেলস্টেশন"; the terminus is printed "নাঃগঞ্জ"), "কাঠপট্টি ঘাট", "নবাবগঞ্জ বাস স্ট্যান্ড".
- Paturia and Aricha are ferry ghats named as bus departure points; `transport.launch_ghat` is the closest key, upazila not stated.
- Mohakhali appears as "বাসস্ট্যান্ড" (Tangail) and "বাস ডিপো" (Kishoreganj); Saidabad as "বাস টার্মিনাল"/"বাসস্ট্যান্ড" on other pages; the DSCC name is used.
- The airport is also a CAAB source entry; kept because the Dhaka district page names it.

## Licence
None stated → `null`.
