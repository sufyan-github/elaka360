# BD_POLICE_CONTACTS_2020_DHAKA — Police HQ "Contacts of Bangladesh Police" (DMP, GMP + Dhaka Range)

**Source:** police.gov.bd → XLSX uploaded 03-10-2020 (trust level 4), sheets `DMP` (Dhaka Metropolitan Police), `GMP` (Gazipur Metropolitan Police) and `Dhaka Range` (13 district blocks). Collected with `bd_police_contacts_2020/fetch.py --division dhaka`, accessed 2026-11-17. `raw/police_contacts_2020_dmp_gmp_dhaka_range.csv` keeps those rows (designations only, no names).

## Collected (182 rows)

| District | police_station | sp_office | control room (`emergency`) |
|---|---|---|---|
| Dhaka (DMP 50 + district 7) | 57 | 1 | 2 (DMP + district) |
| Gazipur (GMP 8 + district 5) | 13 | 1 | 2 (GMP + district) |
| Kishoreganj | 13 | 1 | 1 |
| Tangail | 13 | 1 | 1 |
| Faridpur | 9 | 1 | 1 |
| Narayanganj | 7 | 1 | 1 |
| Narsingdi | 7 | 1 | 1 |
| Manikganj | 7 | 1 | 1 |
| Shariatpur | 7 | 1 | 1 |
| Munshiganj | 6 | 1 | 1 |
| Madaripur | 5 | 1 | 1 |
| Gopalganj | 5 | 1 | 1 |
| Rajbari | 5 | 1 | 1 |

Per thana:
- **Phone:** the OC's "New Number" (an official 01320-series SIM). The duty officer's number is attached on all 154 thanas; pre-2020 and landline numbers are in `extra_json`.
- **E-mail:** official e-mail on 133 rows; 24 of these are thana gmail or yahoo addresses.
- **Upazila:** `upazila_en` is set on 147 of 154 thanas.
  - DMP and GMP rows hold the metro thana, e.g. Ramna, Kotwali, Uttara East, or GMP Basan and Tongi East; GMP "Sadar" is mapped to Gazipur Sadar.
  - It is empty for thanas that are not upazilas: Ashulia, South Keraniganj, Fatullah, Siddhirganj, Madhabdi, Bangabandhu Setu East and Sakhipur (Shariatpur).
  - District "Sadar"/Kotwali/Palong/Joydebpur thanas are mapped to the Sadar upazila.
- **SP offices:** names are composed as "SP Office, X" (sheet heading "District Police X"; the designation is "Police Super").
- **Not collected:**
  - the Dhaka Range office and "RRF, Dhaka";
  - DMP's non-thana "OC" posts (Ration Store, Telephone);
  - DMP divisional control rooms (POM-East etc.). Only the "DMP Control Room" and "DMP Hot-line" are taken.

## Data quality
- Spellings as published (Asulia, Nobabgonj, Soriotpur, "Bangabanddu Setu East"); the Shariatpur control room is named "Control Room, District Police Soriotpur".
- The Tangail SP e-mail is printed "Sptangail@Police.gov.bd" (kept as published).
- Six years old; not cross-checked against the 2026 portals by this collector.

## Licence
None stated → `null`.
