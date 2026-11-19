# DISTRICT_PORTAL_BANKS_DHK_2026 — bank lists on Dhaka Division district portals

**Source (trust level 4, accessed 2026-11-17):** the "ব্যাংক" pages of the 13 DC portals. Six give usable branch/office numbers; `raw/` keeps their page text with mobile numbers redacted. Licence: none stated → `null`.

**fetch.py:** new `main_dhaka()` with one parser per page layout (Narayanganj "♣" blocks in English, Tangail and Manikganj/Rajbari tables, Gopalganj numbered lines, Faridpur bank headings + manager tables); same contact rule as Rangpur (landlines only).

## Collected: 118 rows (`finance.bank`)

| District | Rows | What the page gives |
|---|---|---|
| Gopalganj | 31 | one line per bank: name + numbers (", গোপালগঞ্জ" added) |
| Faridpur | 21 | bank heading + branch manager's office number (branch named in 19 rows; Grameen Bank's zonal and area numbers merged into one row) |
| Tangail | 21 | bank, address, phone (one office per bank in Tangail town) |
| Narayanganj | 20 | branch name, address, "Tel" numbers (English; name in `name_en`) |
| Manikganj | 13 | "<manager post>, <bank>, মানিকগঞ্জ" + number |
| Rajbari | 12 | bank (Sonali's two branches named) + number |

- **Phone:** 101 of 118. Mobile numbers are dropped (Gopalganj 39, Tangail 10, Rajbari 1), so 17 rows have no phone (only mobiles listed, or no number at all). Fax, telex, SWIFT and branch e-mails (Narayanganj) are not copied.
- **Address:** 41 rows (Narayanganj, Tangail).
- **Names:** composed where the page names only the bank ("<bank>, <district>" or "<bank>, <branch>, ফরিদপুর"); each note says so.

## Not used
- Dhaka and Gazipur: bank names and websites only.
- Shariatpur: the upazilas where each bank has a branch, without contacts.
- Kishoreganj: prose list of town branches without contacts.
- Madaripur: mostly names, mixed with NGOs.
- Narsingdi and Munshiganj: no bank page.

## Doubts
- Lists are undated; Narayanganj numbers are old 7-digit Dhaka numbers without "02", Faridpur numbers are 5 digits without the 0631 area code.
- 096xx numbers (Gopalganj, Narayanganj) are IP-phone numbers, kept as printed.
