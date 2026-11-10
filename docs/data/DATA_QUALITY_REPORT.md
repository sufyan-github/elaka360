# Data quality report

Produced by `python3 pipelines/validate_seed.py`, which runs in CI on every push. Current result: **0 failures, 4 warnings.**

| Check | Result |
|---|---|
| Unicode NFC on every text field | Pass |
| Stable id ranges (divisions 10001–08, districts 20001–64, upazilas 30001–495, unions 40001–44541, city corporations 50001–13, pourashavas 60001+) | Pass |
| Every row's parent exists and is the right level | Pass |
| No duplicate union/upazila under the same parent; unique paths | Pass (3 nuhil duplicates removed; Natai North/South kept, same English name but different Bangla) |
| No digits or "up" suffixes in union/upazila names | Pass (5 fixed) |
| Policy: eligible ⇒ official/secondary + source with URL; verified ⇒ official | Pass |
| Coordinates inside Bangladesh | Pass |
| Seed vs master: every difference tracked, no stale entries | Pass (16 tracked differences) |
| Population: district sums vs division totals | 4 warnings, all ±1 person (source rounding: Chattogram −1, Khulna +1, Barishal +1, Rangpur +1) |

## Known gaps

From `data/seed/qa/known_gaps.csv`:

- No record has official (Tier 1) evidence yet.
- About 33–40 unions are missing against the official count of 4,571–4,578. All 4,538 unions in the seed are community data and unpublished.
- Eidgaon, Madhyanagar, Dasar and Guimara upazilas still have no unions assigned.
- There are no upazila or union boundaries and no BBS geocodes below division level. District areas are computed from polygons, except Rajshahi, which uses the official figure.
- The 14 Rajshahi pourashavas are unverified. BBS 2011 lists 15.
- There are no wards, mouzas or villages.
- Population basis is mixed. Divisions and districts use 2022 census-adjusted figures; Rajshahi's upazilas use enumerated figures. The basis is stored on every row and shown in the UI. Do not add figures across levels.

## Hotlines

7 of 10 are published. They have secondary evidence: Wikipedia, and The Financial Express for 102. 16263, 1098 and 16430 have no source in this build, so they are not served as callable numbers. 16163 (the retired fire line) and 100 (not a Bangladesh number) are not in the data.
