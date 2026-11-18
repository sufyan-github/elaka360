# DISTRICT_PORTAL_BANKS_BAR_2026 — bank lists on Barishal Division DC portals

**Source** (trust level 4, accessed 2026-11-18): the "ব্যাংক" pages of patuakhali, pirojpur and bhola `.gov.bd`. Licence: none stated → `null`. Lists are undated.

**fetch.py:** new `main_barishal()` with one parser per layout, and a `barishal` entry in `SITES`.
- `raw/` keeps only the columns used, with mobiles redacted.
- Patuakhali's heads' names and Pirojpur's residence numbers are left out.

## Collected: 58 rows (`finance.bank`)

| District | Rows | With phone | With address | Layout |
|---|---|---|---|---|
| Patuakhali | 24 | 5 | 0 | serial / bank / head's name+post (not copied) / one number → "<bank>, পটুয়াখালী" |
| Pirojpur | 20 | 20 | 20 | serial / "<post>, <bank>, <branch>, <address>" / office / residence (not copied) |
| Bhola | 14 | 13 | 14 | serial / bank / address / phone |

## Contact rule
- Only landlines are kept: 19 Patuakhali mobiles are dropped, and Pirojpur's residence column is not copied.
- 09677557141 (BRAC, Patuakhali) is a non-mobile number and is kept.
- No e-mails, routing numbers or names.

## Composed names (original in `extra_json`)
- Pirojpur: "<bank>, <branch>"; the AGM/RM offices become "<bank> (এজিএম কার্যালয়)" / "(আরএম কার্যালয়)"; "<bank>, পিরোজপুর" where no branch is given. Row 8 "অগ্রণী ব্যাংক, উপজেলা কমপ্লেক্স" keeps the location as its distinguishing part.
- Bhola: ", ভোলা" added where missing.

## Not used
- **Barishal and Barguna:** the pages list banks with head-office web links only; no branch in the district.
- **Jhalokathi:** the list is a scanned PDF (CamScanner) with no text layer.

## Doubts
- Names are as printed ('ব্রাক', 'রুপালী', 'ফাস্ট', 'আল আরাফাহ ইসলামী ব্যাংক ব্যাংক').
- Pirojpur uses the old 0461 numbers.
- No upazila is set: Pirojpur rows at পাড়েরহাট/হুলারহাট name no upazila.
