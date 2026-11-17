# BD_POLICE_CONTACTS_2020_RANGPUR — Police HQ "Contacts of Bangladesh Police" (RRMP + Rangpur Range)

**Source:** police.gov.bd → XLSX uploaded 03-10-2020 (trust level 4), sheets `RRMP` (Rangpur Metropolitan Police) and `Rangpur Range`. Collected with `bd_police_contacts_2020/fetch.py --division rangpur`, accessed 2026-11-17. `raw/police_contacts_2020_rrmp_rangpur_range.csv` keeps those rows (designations only, no names).

## Collected (84 rows)
| District | police_station | sp_office | control room (`emergency`) |
|---|---|---|---|
| Rangpur (RpMP 6 + district 8) | 14 | 1 | 2 (RpMP + district) |
| Dinajpur | 13 | 1 | 1 |
| Kurigram | 11 | 1 | 1 |
| Gaibandha | 7 | 1 | 1 |
| Nilphamari | 6 | 1 | 1 |
| Thakurgaon | 6 | 1 | 1 |
| Lalmonirhat | 5 | 1 | 1 |
| Panchagarh | 5 | 1 | 1 |

Per thana:
- **Phone:** the OC's "New Number" (an official 01320-series SIM). Duty-officer, pre-2020 and BTCL numbers are in `extra_json`.
- **E-mail:** official e-mail on 44 rows; 18 of these are thana gmail addresses.
- **Upazila:** `upazila_en` is set on 63 of 67 thanas. RpMP rows hold the metro thana: Kotwali, Tajhat, Mahiganj, Haragachh, Parshuram, Hajirhat.
  - It is empty for Kotwali (Rangpur district sheet, ambiguous with RpMP Kotwali), Dushmara, Kachakata and Ruhiya.
- **SP offices:** names are composed as "SP Office, X", because the sheet headings read "X District".
- **Not collected:** the DIG range office and the Rangpur RRF blocks.

## Data quality
- Lalmonirhat "OC Kaligonj Thana" repeats Aditmari's serial (27), official number, current number and e-mail (copy error in the source); kept with id suffix and a note.
- Nilphamari SP e-mail printed as "spnilphamari@police.gov.com" (kept as published); some landlines malformed ("05526/72025", "63599*").
- Six years old; not cross-checked against the 2026 Rangpur portals by this collector.

## Licence
None stated → `null`.
