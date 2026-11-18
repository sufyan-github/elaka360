# BB_SCHEDULED_BANKS_BAR_2026 — Bangladesh Bank, Scheduled Banks Statistics (Apr–Jun 2026), Barishal Division

**Source:** bb.org.bd quarterly Scheduled Banks Statistics, April–June 2026 (as on 30-06-2026), 8.5 MB PDF. It is not committed; `fetch.py --division barishal` re-downloads it and parses it with pdftotext. Trust level 4. Accessed 2026-11-18.

## Branch list: not available
There is no public branch list (names, addresses, routing numbers), and district branch counts are not published.

## Collected (facts only, 130 rows)
- **Branches (Table-3.16):** scheduled bank branches in the division at end-June 2026 — urban 306, rural 271, **total 577**. Transcribed from the table image: PDF page 36, printed p. 28 (Table-3.16 Concld.), "Barishal division" column.
- **Deposits and advances (Table-1, Concl'd):** division and all 6 districts, in BDT lakh, with per-capita values.

  | Area | Deposits (BDT lakh) | Advances (BDT lakh) |
  |---|---:|---:|
  | Barishal District | 1,941,104 | 711,921 |
  | Barishal Division | 4,627,517 | 1,948,623 |
- **Deposit accounts (Table-33):** division (8,413,368 accounts), 6 districts and 46 thanas, plus thana deposit amounts.
  - Thana names are as spelled by BB, mapped per district: Pathorghata, Taltoli, Gouranadi, Hijla, Charfeshion, Monpura, Jhalokati Sadar, Kathalia, Bawphal, Mirjaganj, Kaowkhali.
  - `upazila_en` is set on 41 thanas: every upazila of the division except Barishal Sadar, which BB reports only through the BMP thanas. It is empty for:
    - the BMP thanas: Kotwali_Barishal, Airport;
    - Kazirhat, Char Shasivuson (Shashibhushan) and Mohipur (police stations, not upazilas).

## Data quality
- Table-1 per-capita values use BB's population basis (Barishal division 9,550,609).
- Table-33 counts are deposit accounts, not people.
- BB lists only two BMP thanas (Kotwali_Barishal, Airport); Kawnia and Bandar do not appear separately.

## Licence
None stated → `null`.
