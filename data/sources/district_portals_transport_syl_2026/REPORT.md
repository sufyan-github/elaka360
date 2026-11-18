# DISTRICT_PORTALS_TRANSPORT_SYL_2026 — terminals, stations, ghats and airport named on Sylhet Division portals

**Source** (trust level 4, accessed 2026-11-18):
- the "যাতায়াত ব্যবস্থা" / "যোগাযোগ ব্যবস্থা" pages of the moulvibazar and habiganj DC portals;
- the transport and "যোগাযোগ" pages of the upazila portals that name a place: Sylhet Sadar, Beanibazar, Bishwanath, Fenchuganj, Zakiganj, Dakshin Surma, Juri, Shayestaganj, Chhatak, Derai, Dowarabazar, Shalla;
- the Sylhet DC portal "এক নজরে" (for the fact).

All 45 DC and upazila portals were scanned for such pages. The Sylhet DC portal links none, and the Sunamganj DC page names no place. Licence: none stated → `null`.

**fetch.py:** a `sylhet` entry in `SITES` (pages, entries, facts, Let's Encrypt intermediates). Rows are kept only if the phrase is still on the live page. `raw/` keeps only the lines carrying the matched phrases.

## Collected (16)

| District | Category | Name |
|---|---|---|
| Sylhet | bus_terminal | কদমতলী বাস টার্মিনাল (Bishwanath, Dakshin Surma, Sylhet Sadar, Zakiganj, Derai, Habiganj DC pages); বিয়ানীবাজার বাসস্ট্যান্ড (Beanibazar) |
| Sylhet | railway_station | সিলেট রেলওয়ে স্টেশন (normalised); খাজাঞ্চী রেলস্টেশন (Bishwanath, composed); ফেঞ্চুগঞ্জ ষ্টেশন; মাইজগাও ষ্টেশন |
| Sylhet | airport | এম এ জি ওসমাণী আন্তর্জাতিক বিমানবন্দর (Sylhet Sadar; composed) |
| Moulvibazar | railway_station | শ্রীমঙ্গল রেলস্টেশন (Sreemangal; composed from "স্টেশন মাষ্টার, শ্রীমঙ্গল"); কুলাউড়া ষ্টেশন |
| Habiganj | railway_station | শায়েস্তাগঞ্জ রেলস্টেশন (Shayestaganj) |
| Sunamganj | railway_station | ছাতক রেলস্টেশন (Chhatak; composed) |
| Sunamganj | launch_ghat | ছাতক ফেরী ঘাট; আজমপুর নৌকাঘাট and দোহালিয়া নৌকাঘাট (both composed from "আজমপুর/দোহালিয়া নৌকাঘাট"); নেয়ামতপুর নৌকাঘাট |
| Sunamganj | bus_terminal | দিরাই বাসস্ট্যান্ড |

**Facts (1):** Sylhet District railway_stations = 6 (DC "এক নজরে", stations not named).

No coordinates, addresses or contacts. Bus company counter numbers are not copied.

## Gaps
- Not rows:
  - Dhaka-side terminals (Sayedabad, Mohakhali, Kamalapur);
  - company counters (সোবাহানীঘাট, হুমায়ূন চত্বর);
  - route mentions without a named stop: Kamalganj "ঢাকা-ভানুগাছ / শমসেরনগর রেল পথে", Madhyanagar "তাহির উপজেলা থানা ঘাট", Baniachong's unnamed stand.
- Upazila is set only where the page states it (6 rows).

## Doubts
- The Sylhet Sadar page also calls the airport "হযরত শাহাজালাল আন্তর্জাতিক বিমানবন্দর" (Dhaka's name). The airport is also in the CAAB source.
- The ghats are boat or ferry landings; launch_ghat is the closest key.
