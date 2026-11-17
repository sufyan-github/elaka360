# DISTRICT_PORTAL_BANKS_RANG_2026 — bank lists on district portals (Rangpur Division)

**Source:** DC-office portals (trust level 4), accessed 2026-11-17: panchagarh.gov.bd "ব্যাংক", nilphamari.gov.bd "ব্যাংকসমূহ", kurigram.gov.bd "ব্যাংক". `raw/` keeps the extracted table text (mobile numbers redacted; Panchagarh manager column not kept).

## Collected (38 × `finance.bank`)
| District | Rows | Notes |
|---|---|---|
| Panchagarh | 12 | name, street address and 0568- landline per bank (branches in Panchagarh town); bank website in `extra_json.bank_website` |
| Nilphamari | 13 | branch names as printed ("সোনালীব্যাংক, নীলফামারীশাখা" — spaces missing at source); only 2 rows keep a phone (landline); website in `extra_json` |
| Kurigram | 13 | 10 bank rows + 3 regional offices; numbers by post ("ব্যাবস্থাপক", "আঞ্ছলিক ব্যাবস্থাপক"…) in `extra_json.office_numbers`; names composed "<bank>, কুড়িগ্রাম" |

- **Phones:** 27 of 38, landlines only.
- **Not published:** e-mails, coordinates and routing numbers. Only Panchagarh gives addresses.
- **Upazila:** `upazila_en` is empty. The lists are for the district towns but do not say so.

## Contact rule
Branch mobile numbers (Panchagarh 11, Nilphamari 11) are **not copied**: the source does not say whether they are branch lines or managers' personal phones. Managers' names not copied.

## Not usable
- **Rangpur and Gaibandha:** the portals give bank names only.
- **Thakurgaon:** two unnamed PDF attachments.
- **Lalmonirhat:** no bank page.
- **Dinajpur:** the page lists banks with national hotline numbers and alternative street names ("স্টেশন রোড / জেল রোড") rather than branch data. Not used, because its origin is doubtful.

## Data quality
- Panchagarh: several link targets point to another bank's site (the displayed URL is used); "ন্যাশনাল বাংক", "কর্ম্ সংস্থান ব্যাংক" spelled as printed.
- Nilphamari "৬১৪৮১" has no area code; Mercantile "০৫৫১-৬২০০৭-০৮" is a number range.
- Lists are undated.

## Licence
None stated → `null`.
