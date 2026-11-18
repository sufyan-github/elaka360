# Dhaka North City Corporation (dncc.gov.bd)

- **Portal:** dncc.gov.bd (title "ঢাকা উত্তর সিটি কর্পোরেশন"; www.dncc.gov.bd fails TLS verification). Key DHAKA_NORTH_CITY_CORPORATION, `"city": 50001`, accessed 2026-11-17.
- **fetch.py (`rcc/fetch.py`):** new `--city dhaka_north|dhaka_south|narayanganj|gazipur` option; `--division dhaka` without `--city` runs all four into their own folders. No arguments still runs Rajshahi (outputs checked identical).
- **Wards: 54**, in **10 zones** ("লোকেশন ও আয়তন", updated 2026-11-09). areas.csv has the city corporation and wards 1–54 by number (name_bn is a label) with their zone; DNCC publishes no ward names.
  - Zones: 1: 1, 17 · 2: 2–8, 15 · 3: 18–25, 35, 36 · 4: 9–14, 16 · 5: 26–34 · 6: 51–54 · 7: 47–50 · 8: 44–46 · 9: 39, 40, 43 · 10: 37, 38, 41, 42.
  - The page lists the areas (mahallas, sectors, mouza parts) of each ward; they are in facts.csv as `ward_areas` (spellings as printed).
- **Area:** 196.22 km²; extent 90°20′–90°28′ E, 23°44′–23°54′ N (as printed).
- **Population: not published** by DNCC (no figure on any page found).
- **History:** Dhaka Municipality established 1 Aug 1864; DCC divided into DNCC and DSCC under the Local Government (City Corporation) Act 2009 (Amendment 2011). The DNCC page gives no date (DSCC's history: 4 Dec 2011 split, 1 Feb 2012 start).
- **Thanas:** DNCC publishes no thana list (see DHAKA_METRO_POLICE).
- **Not copied:** ward officers' and ward secretaries' lists (names, mobiles); the Nagar Bhaban address is in the city-corporation row's notes.
- Licence: none stated.
