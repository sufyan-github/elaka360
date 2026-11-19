# DISTRICT_PORTAL_BANKS_MYM_2026 — bank lists on Mymensingh Division DC portals

**Source** (trust level 4, accessed 2026-11-18): the bank pages of the sherpur and jamalpur `.gov.bd` DC portals, and the netrokona DC portal's "ব্যাংক/আর্থিক সংস্থা" list (/pages/bank-financial-org). Licence: none stated → `null`. The lists are undated.

**fetch.py:** new `main_mymensingh()` with one parser per layout, and a `mymensingh` entry in `SITES`. `raw/` keeps only the text used: mobiles are redacted and the e-mail lines and the people's names are left out.

## Collected: 62 rows (all `finance.bank`)

| District | Rows | With phone | With address | Layout |
|---|---|---|---|---|
| Sherpur | 15 | 11 | 10 | "♣ <bank> - <branch>" blocks under upazila headings (address, telephone and e-mail lines) |
| Jamalpur | 42 | 0 | 0 | numbered "<bank>, <branch> শাখা।" lines; no numbers |
| Netrokona | 5 | 4 | 4 | framework list (bank, branch, address, head/contact phones and mobiles, names) |

## Contact rule
- Only landlines are kept, as printed. Numbers after the first share its area code (e.g. "0931-61318; 61403"); "এক্সট" / "এক্সটেনশন" extensions go in `extra_json` or in the phone as "ext".
- Mobiles dropped: Sherpur 5, Netrokona 14.
- E-mails are not copied (bangla.net or bank domains, none a government address). Managers' and contact persons' names are not copied.

## Names (original in `extra_json`)
- **Sherpur:** "<bank>, <branch>" from the heading. Where the heading names no branch ("সোনালী ব্যাংক লিমিটেড -"), the first address line is used as the place (noted). `upazila_en` comes from the page's upazila headings (Sherpur Sadar, Nalitabari, Jhenaigati, Nokla, Sreebordi).
- **Jamalpur:** as printed, with the doubled "শাখা শাখা" reduced. No upazila is given.
- **Netrokona:** "<bank>, <branch>".

## Left out
- Sherpur's second "অগ্রণী ব্যাংক লিমিটেড, শেরপুর, শেরপুর" block repeats the first (same number and e-mail).
- Jamalpur's "২৮। জনতা ব্যাংক লিঃ, জামালপুর প্রধান শাখা" repeats no. 25. Serial ৯ is printed twice; both rows are kept.
- One Sherpur number printed with mixed Bangla and ASCII digits ("৬১২৩৮8", Sonali Jhenaigati) is not copied; it is kept in `extra_json`.

## Not used
- **Mymensingh:** the DC portal's bank list is empty and its menu's "ব্যাংক" entry links only bb.org.bd.
- **Netrokona's static page "নেত্রকোণা জেলার ব্যাংক":** a 4-page PDF whose text layer is a legacy, non-Unicode Bangla font. The portal's own 5-entry list is used instead.

## Doubts
- The Sherpur numbers use the 0931 / 09324 codes as printed; Sonali Nalitabari is printed 0931-73011.
- Netrokona's list mixes "নেত্রকোনা" and "নেত্রকোণা" spellings.
