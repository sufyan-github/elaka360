# BD_POLICE_CONTACTS_2020 — Police HQ "Contacts of Bangladesh Police" (RMP + Rajshahi Range)

**Source:** police.gov.bd → "New Phone Numbers" → XLSX uploaded 03-10-2020 (trust level 4). Accessed 2026-11-12. Only sheets
`RMP` and `Rajshahi Range` are used; `raw/police_contacts_2020_rmp_rajshahi_range.csv` keeps those rows (designations only, no names).
The full 1.5 MB workbook is re-downloaded by `fetch.py`.

## Collected (100 rows, all districts of the division)
| District | police_station | sp_office | control room (`emergency`) |
|---|---|---|---|
| Rajshahi (RMP 12 + district 8) | 20 | 1 | 2 (RMP + district) |
| Naogaon | 11 | 1 | 1 |
| Natore | 7 | 1 | 1 |
| Chapainawabganj | 5 | 1 | 1 |
| Bogura | 12 | 1 | 1 |
| Joypurhat | 5 | 1 | 1 |
| Pabna | 11 | 1 | 1 |
| Sirajganj | 12 | 1 | 1 |

Per thana: OC "New Number" (01320-series official SIM) as `phone`; duty-officer new number, pre-2020 number and BTCL landline
(raw, often missing the leading 0) in `extra_json`; official e-mail where given (82 rows). Names are the source's English spellings
(e.g. "Godogari Model PS", "Bodolgasi PS"); `upazila_en` mapped to standard names (78 rows) — empty for Ataikula, Aminpur,
Bangabandhu Bridge West, Salanga, Enayetpur. No Bangla names, addresses or coordinates. No police outposts (fari) are listed.
RRF and range-office posts are not collected.

## Data quality
- Six years old, but every OC/duty number checked against the 2026 portals (RMP 12, Rajshahi 8, Pabna 9, Sirajganj 9 upazila thanas) is identical.
- Pabna "OC Ataikula PS" e-mail duplicates Sathia's (ocsathiyapabna@police.gov.bd). Some e-mails are Gmail addresses of the thana.
- Landline values are malformed in places (e.g. "722456004", "017133-7304").

## Licence
None stated → `null`.
