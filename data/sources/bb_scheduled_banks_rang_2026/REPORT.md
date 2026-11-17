# BB_SCHEDULED_BANKS_RANG_2026 — Bangladesh Bank, Scheduled Banks Statistics (Apr–Jun 2026), Rangpur Division

**Source:** bb.org.bd quarterly Scheduled Banks Statistics, April–June 2026 (as on 30-06-2026), 8.5 MB PDF (not committed; `fetch.py --division rangpur` re-downloads and parses it with pdftotext). Trust level 4. Accessed 2026-11-17.

## Branch list: not available
No public branch list (names, addresses, routing numbers); district branch counts are not published.

## Collected (facts only, 170 rows)
- **Branches (Table-3.16 Concld.):** scheduled bank branches in the division at end-June 2026 — urban 345, rural 428, **total 773**. Transcribed from the image, PDF page 36 / printed p. 28.
- **Deposits and advances (Table-1):** division and the 8 districts, in BDT lakh, with per-capita values.

  | Area | Deposits (BDT lakh) | Advances (BDT lakh) |
  |---|---:|---:|
  | Rangpur District | 1,194,784 | 1,048,160 |
  | Rangpur Division | 4,536,929 | 4,162,941 |
- **Deposit accounts (Table-33):** division, 8 districts and 61 thanas, plus thana deposit amounts.
  - Thana names are as spelled by BB, mapped per district: Birol → Biral, Sayedpur → Saidpur, Rowmari → Raomari, Rajibpur → Char Rajibpur, Dinajpur "Kotwali" → Dinajpur Sadar.
  - `upazila_en` is empty for the RpMP thanas in Rangpur district ("Kotwali", Haragach, Tajhat) and for Thakurgaon "Ruhia".

## Data quality
- Table-1 per-capita values use BB's population basis (e.g. Rangpur division 18,454,427; BB cites the 2023 census preliminary report).
- Table-33 counts are deposit accounts, not people. BB spells Gaibandha "Gaibandah".

## Licence
None stated → `null`.
