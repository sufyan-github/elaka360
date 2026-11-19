# BB_SCHEDULED_BANKS_SYL_2026 — Bangladesh Bank, Scheduled Banks Statistics (Apr–Jun 2026), Sylhet Division

**Source:** bb.org.bd quarterly Scheduled Banks Statistics, April–June 2026 (as on 30-06-2026), 8.5 MB PDF. It is not committed; `fetch.py --division sylhet` re-downloads it and parses it with pdftotext. Trust level 4. Accessed 2026-11-18.

## Branch list: not available
There is no public branch list (names, addresses, routing numbers), and district branch counts are not published.

## Collected (facts only, 118 rows)
- **Branches (Table-3.16):** scheduled bank branches in the division at end-June 2026 — urban 397, rural 428, **total 825**. Transcribed from the table image: PDF page 36, printed p. 28 (Table-3.16 Concld.), "Sylhet division" column.
- **Deposits and advances (Table-1, Concl'd):** division and all 4 districts, in BDT lakh, with per-capita values.

  | Area | Deposits (BDT lakh) | Advances (BDT lakh) |
  |---|---:|---:|
  | Sylhet District | 5,261,398 | 1,003,597 |
  | Moulvibazar District | 1,771,615 | 309,060 |
  | Habiganj District | 1,036,344 | 308,094 |
  | Sunamganj District | 793,127 | 236,536 |
  | Sylhet Division | 8,862,485 | 1,857,287 |
- **Deposit accounts (Table-33):** division (9,535,742 accounts), 4 districts and 45 thanas, plus thana deposit amounts. The thana accounts add up to each district total.
  - Thana names are as spelled by BB, mapped per district: Banichang, Baralekha, Rajanagar, Bishwamvarpur, Dakshin Sunamganj (→ South Sunamganj), Dowar Bazar, Madhaya Nagar, Salla, Biani Bazar.
  - `upazila_en` is set on 39 thanas. Sylhet Sadar has no thana of its own: BB reports it only through the SMP thanas.
  - `upazila_en` is empty for the SMP thanas: Kotwali_Sylhet, Jalalabad, Bimanbondar (Airport), Shahporan, Maglabazar (Moglabazar), and "Dakhin Surma".

## Data quality
- **"Dakhin Surma":** it is listed beside the SMP thanas, so it is read as the SMP South Surma thana and not mapped to Dakshin Surma upazila. This is flagged and may need review.
- **Population basis:** Table-1 per-capita values use BB's population basis (Sylhet division 11,690,262).
- **Accounts:** Table-33 counts are deposit accounts, not people.

## Licence
None stated → `null`.
