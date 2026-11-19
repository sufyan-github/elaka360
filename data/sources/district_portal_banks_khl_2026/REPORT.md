# DISTRICT_PORTAL_BANKS_KHL_2026 — bank branch lists on Khulna Division DC portals

**Source** (trust level 4, accessed 2026-11-18): the bank pages of the district portals meherpur, narail, chuadanga, kushtia, magura and bagerhat `.gov.bd`. Licence: none stated → `null`. Lists are undated.

**fetch.py:** new `main_khulna()` with one small parser per page layout, and a `khulna` entry in `SITES`. No other change.
- `raw/` keeps the page text with mobiles and e-mails redacted; for Bagerhat only the bank and office/phone columns, because the head's name and mobile share a cell.

## Collected: 91 rows (`finance.bank`)

| District | Rows | With phone | With address | With upazila | Layout |
|---|---|---|---|---|---|
| Kushtia | 17 | 0 | 0 | 0 | 'N. <post>, <bank>, …' lines; post stripped, ', কুষ্টিয়া' added where missing |
| Meherpur | 16 | 14 | 0 | 3 | bank (first row) / branch / telephone / mobile / e-mail (government banks only) |
| Chuadanga | 15 | 0 | 0 | 0 | '<bank> লিঃ, চুয়াডাঙ্গা' names only |
| Magura | 15 | 0 | 0 | 0 | bank / address ('মাগুরা', 'ঐ' = ditto) → '<bank>, মাগুরা' |
| Bagerhat | 15 | 15 | 15 | 0 | bank / head / office + 'ফোন-…' / services / type; the table is printed twice and read once |
| Narail | 13 | 12 | 0 | 0 | '<post>, <bank>, <branch>' / phone |

## Contact rule
- Only landlines are kept. Meherpur's mobile column (5 numbers) and Bagerhat's heads' mobiles (in the same cell as their names) are not copied.
- No e-mails: Meherpur's are bangla.net / gmail / bank addresses. No routing numbers, coordinates or managers' names.

## Composed names (original in `extra_json`)
- Meherpur: "<bank> ব্যাংক, <branch>". Branch names are printed without spaces ("মেহেরপুরশাখা"), one has "মেহেররপুর". Upazila is set where the branch names Gangni or Mujibnagar.
- Narail: "<bank>, <branch>" or "<bank>, নড়াইল". The regional office is "কৃষি ব্যাংক আঞ্চলিক কার্যালয়, নড়াইল". The post is in `extra_json`.
- Bagerhat: "<bank>, <X শাখা>", "<bank> রিজিওনাল অফিস, বাগেরহাট" or "<bank>, বাগেরহাট".

## Not used
- **Khulna:** the bank list is a 2-page PDF exported from Excel (address, office landline per bank). Its text layer extracts garbled (Bangla vowel signs in the wrong order), so names cannot be read reliably.
- **Satkhira:** the bank module has 4 near-empty entries.
- **Jhenaidah:** 1 'test' entry.
- **Jashore:** the module is empty and the DC menu's 'ব্যাংক' link is '#'.

## Doubts
- Names are as printed, including misspellings ('সনালী', 'বাংলদেশ', 'অগ্রনী', 'ফাষ্ট', 'স্টান্ডার্ট').
- Narail and Bagerhat numbers lack the new 0247… format (old area codes 0481, 0468).
