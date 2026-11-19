# DISTRICT_PORTAL_BANKS_SYL_2026 — bank lists on Sylhet Division DC portals

**Source** (trust level 4, accessed 2026-11-18): the bank pages of the sylhet, habiganj and moulvibazar `.gov.bd` DC portals. Licence: none stated → `null`. The lists are undated.

**fetch.py:** new `main_sylhet()` with one parser per layout, and a `sylhet` entry in `SITES`.
- The Let's Encrypt intermediates are added for this run.
- `raw/` keeps only the columns used: no e-mail column, mobiles redacted.

## Collected: 71 rows

| District | Rows | With phone | With address | Layout |
|---|---|---|---|---|
| Sylhet | 41 (37 `finance.bank`, 4 `finance`) | 41 | 38 | bank / "<post>, <branch/area>, সিলেট" / numbers / e-mail |
| Habiganj | 20 | 0 (15 numbers in `extra_json`) | 0 | same columns; numbers are 5-digit local ones |
| Moulvibazar | 10 | 0 | 6 | bank / branch or road (no numbers) |

## Contact rule
- Only landlines are kept. 2 mobiles are dropped, one of them run together with a landline in the same cell.
- **Sylhet:** the e-mail column is not copied (mostly gmail or bangla.net addresses). Numbers after the first share its 0821 area code as printed (e.g. "0821-716298; 722183").
- **Habiganj:** office numbers are printed as 5-digit local numbers with no area code. They are kept only as `office_number_as_printed` in `extra_json`, and no area code is added. Residence ("বাসা") numbers are not copied.
- No routing numbers, managers' names or coordinates.

## Composed names (original in `extra_json`)
- **Sylhet:** "<bank>, <first place>". The office type is added when the post heads one: (আঞ্চলিক কার্যালয়), (বিভাগীয় কার্যালয়), (জোনাল অফিস), (ডিজিএম কার্যালয়). ", সিলেট" is added where no place is given (NBP, IDLC, Social Investment Bank).
- **Habiganj:** "<bank>, <branch>"; ", হবিগঞ্জ" where no branch is given.
- **Moulvibazar:** "<bank>, <branch/road>".
- IDLC, ICB, National Credit and শিল্প ঋণ সংস্থা are top-level `finance` (not banks).

## Not used
- **Sunamganj** (/pages/bank-financial-org): bank and insurer names only; every branch, address and phone field is empty.
- **Moulvibazar:** 2 rows naming several or unnamed branches (বাংলাদেশ কৃষি ব্যাংক "মৌলভীবাজার ও বিভিন্ন উপজেলা শাখা"; UCB "কুলাউড়া / শ্রীমঙ্গল / মৌলভীবাজার শাখা").

## Doubts
- Names are as printed: "ইসলামীব্যাংকলিমিটেড", "গ্রামীণব্যাংক", "শাখঅ", "শাঃ", "আঞ্চলিক কার্যালয".
- The Sylhet list is old (07xxxx numbers, Bank Al-Falah, Habib Bank).
- No upazila is set.
