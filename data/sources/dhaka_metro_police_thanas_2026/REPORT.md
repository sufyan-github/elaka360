# DHAKA_METRO_POLICE_THANAS_2026 — Dhaka Metropolitan Police

**Source:** dmp.gov.bd "Find Your Local Police" (per-station address and numbers) and "Contact Us" (Commissioner, control room), plus the Dhaka DC portal's city-thana list for Hatirjheel. Trust level 4, accessed 2026-11-17. `"city": [50001, 50002]`.

**fetch.py (`rmp_thanas_2026/fetch.py`):** new `--city dhaka|gazipur` option (`--division dhaka` alone runs both); `main_dmp()` parses the station blocks. No arguments still runs Rajshahi (outputs checked identical).

## Collected: 52 rows (all Dhaka District)
- **50 × `emergency.police_station`:** 49 DMP stations + Hatirjheel (DC list only, no contacts).
  - Phone: the duty officer's T&T landline and the OC's official mobile (01713-37/38/39xxxx or 01769-05xxxx as published by DMP); for 3 incomplete entries without an OC part (Sutrapur, Tejgaon Industrial, Uttara West) only the duty-officer numbers. Phone on 49 of 50 (not Hatirjheel).
  - `extra_json`: duty-officer mobile, OC mobile, DMP PABX extension, fax; `email`: oc…@dmp.gov.bd (45 of 50).
  - Address: as printed, in English (48; Turag's is blank at source, Hatirjheel has none).
  - `upazila_en` holds the metropolitan thana (not an upazila).
- **1 × `government.sp_office`:** DMP Commissioner's office — 9331555, 01320-037000, pc@dmp.gov.bd, pcdmp@police.gov.bd (no HQ address on the page).
- **1 × `emergency`:** DMP Control Room — 9575500, 01817602050, fax 9559933.
- **facts:** 50 police stations; 0 placed in a city corporation.

## City corporation
**0 of 50 thanas placed** (`area_en` empty): no official source names the city corporation of each DMP thana (see DHAKA_METRO_POLICE).

## Doubts
- The DMP list is undated; many landlines are old 7-digit numbers. Some entries are mislabelled at source (the Tejgaon Industrial block is headed "Sutrapur Police Station:"; Shyampur repeats Sutrapur's extension), kept in `extra_json`.
- Not copied: inspector-investigation mobiles, officers' names.

## Licence
None stated → `null`.
