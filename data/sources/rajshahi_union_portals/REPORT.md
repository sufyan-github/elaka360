# Rajshahi District union parishad portals

- **Method:** union list from the district page → each union portal → menu item "এক নজরে" → label matcher extracts facts, keeping the printed label and value in `notes`.
- **Coverage: 64 of 72** (`raw/coverage.csv`). No এক নজরে item: মৌগাছি, ইউসুফপুর, সরদহ, নিমপাড়া, দেওপাড়া, সরঞ্জাই, কাচাড়ী কোয়ালিপাড়া; ভায়ালক্ষীপুর's page returns 404.
- **facts.csv (158).** Manual review encoded in `fetch.py`: SKIP 5 (misaligned rows), MANUAL 5 (checked against page text), DOUBT 6 (implausible or copied values).

## Caveats

- Ward counts are stated on only 3 pages (চারঘাট, আষাড়িয়াদহ, দ্বীপপুর: 9 each); none were inferred.
- Units vary (km², square miles, acres) and are recorded in `unit`. Bagmara's per-union "আয়তন" has no unit ("unstated, probably hectares").
- Implausible values flagged: পাকড়ী "2199 km²", মাটিকাটা "185 km²", কলমা "3,000 persons"; বাউসা repeats আড়ানী's figures; হরিয়ান cites a "2021 census".
- Prefer BBS 2022 (`bbs_census_2022/`) for population.
