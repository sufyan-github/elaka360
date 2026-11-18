# DISTRICT_PORTAL_BANKS_CTG_2026 — bank branch lists on Chattogram Division DC portals

**Source** (trust level 4, accessed 2026-11-17): the "ব্যাংক" pages of the district portals comilla, feni, brahmanbaria, rangamati, noakhali, chandpur, chittagong, khagrachhari and bandarban `.gov.bd`. Licence: none stated → `null`. Lists are undated.

**fetch.py:** new `main_chattogram()` with one small parser per page layout, and a `chattogram` entry in `SITES`. No other change.
- Numbers separated by single spaces are split before filtering.
- `raw/` keeps the page text with mobiles redacted, including mistyped 12-digit ones.

## Collected: 382 rows (`finance.bank`)

| District | Rows | With phone | With address | With upazila | Layout |
|---|---|---|---|---|---|
| Noakhali | 134 | 61 | 134 | 75 | bank (row-spanning) / branch / address / phone; upazila only where the address names one |
| Brahmanbaria | 127 | 16 | 8 | 97 | town table (30) + per-upazila tables (Kasba 34, Ashuganj 25, Nabinagar 11, Bijoynagar 10, Akhaura 9, Sarail 8) |
| Cumilla | 33 | 33 | 33 | 0 | bank (branch) / address / phone, Cumilla town |
| Chattogram | 27 | 27 | 0 | 0 | bank / post of the listed officer / phone, Chattogram city |
| Chandpur | 19 | 0 | 12 | 0 | bank / address; Karmasangsthan Bank's cell lists 7 branches (one row each) |
| Bandarban | 13 | 13 | 0 | 0 | '<post>, <bank>' / phone |
| Feni | 10 | 10 | 1 | 0 | bank / phone (5 digits, no area code) |
| Rangamati | 10 | 10 | 9 | 0 | bank / address / phone |
| Khagrachhari | 9 | 7 | 0 | 0 | bank, branch / head's post / phone |

## Contact rule
- Only landlines are kept. Mobile numbers are dropped: Brahmanbaria 99, Noakhali 54, Khagrachhari 2, Feni 1, Chattogram 1.
- No e-mails, routing numbers, coordinates or managers' names.

## Composed names (original in `extra_json`)
- ", <district town>" is added where a name has no place (Cumilla, Feni, Rangamati, Chandpur, Khagrachhari).
- Chattogram and Bandarban rows are named "<bank>, <district>" (Bandarban regional offices: "<bank> আঞ্চলিক কার্যালয়, বান্দরবান"); the post is kept in `extra_json`.
- Brahmanbaria upazila rows without a place get ", <upazila>".

## Not used
- Cox's Bazar: bank names and websites only.
- Lakshmipur: the bank module has 4 names without branch or contacts.
- Cumilla's second table: run-together text without spaces.
- Brahmanbaria: one legacy-font (non-Unicode) upazila table (Bancharampur), garbled legacy-font names, and an insurance table.
- The divisional portal's bank page.

## Doubts
- **Phone numbers:**
  - Several Cumilla numbers repeat across different banks at source (e.g. 081-65886 for 3 banks).
  - Feni, Brahmanbaria and Chattogram numbers lack the area code.
  - Rangamati ranges ("0351-61701-2") are kept as printed.
- **Duplicates:** 3 Akhaura rows were listed twice; their numbers are merged. Some branches appear in both Brahmanbaria's town table and an upazila table.
- **Upazila:** set only where the source names it (Brahmanbaria upazila column; Noakhali addresses naming an upazila, or "সদর, নোয়াখালী" → Noakhali Sadar). Town names such as Chowmuhani or Maijdee are not mapped.
