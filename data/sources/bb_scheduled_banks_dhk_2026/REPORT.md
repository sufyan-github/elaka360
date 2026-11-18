# BB_SCHEDULED_BANKS_DHK_2026 — Bangladesh Bank, Scheduled Banks Statistics (Apr–Jun 2026), Dhaka Division

**Source:** bb.org.bd quarterly Scheduled Banks Statistics, April–June 2026 (as on 30-06-2026), 8.5 MB PDF. It is not committed; `fetch.py --division dhaka` re-downloads it and parses it with pdftotext. Trust level 4. Accessed 2026-11-17.

## Branch list: not available
There is no public branch list (names, addresses, routing numbers), and district branch counts are not published.

## Collected (facts only, 379 rows)
- **Branches (Table-3.16):** scheduled bank branches in the division at end-June 2026 — urban 2,613, rural 1,341, **total 3,954**. Transcribed from the table image, PDF page 35 / printed p. 27.
- **Deposits and advances (Table-1):** division and the 13 districts, in BDT lakh, with per-capita values.

  | Area | Deposits (BDT lakh) | Advances (BDT lakh) |
  |---|---:|---:|
  | Dhaka District | 112,236,884 | 114,071,268 |
  | Dhaka Division | 133,931,134 | 122,703,581 |
- **Deposit accounts (Table-33):** division (75,773,175 accounts), 13 districts and 153 thanas, plus thana deposit amounts.
  - Thana names are as spelled by BB, mapped per district: Salda → Saltha, Mithamon → Mithamain, Kotwalipara → Kotalipara, Serajdikhan → Sirajdikhan, Tongi Bari → Tongibari, Arihazar → Araihazar, Shivalaya → Shibalaya, Gooshairhat → Gosairhat, Damodiya → Damudya, Zajira → Zanjira, Shakhipur → Sakhipur.
  - Sadar-equivalents: Kotwali_Faridpur → Faridpur Sadar, Palong/Sadar → Shariatpur Sadar, Bandar(M) → Bandar.
  - `upazila_en` is set on 89 thanas. It is empty for the DMP and GMP thanas (incl. Kotwali_Dhaka, Dhaka Int. Airport, Sher-E-Bangla Nagar, Tejgaon I/A), Ashulia, South Keraniganj, Fatullah(M), Siddhirganj, Madhabdi and Sakhipur (Shariatpur).
  - "Joydebpur (Gazipur)/" is kept as published and not mapped, because the table also lists "Gazipur Sadar".

## Data quality
- Table-1 per-capita values use BB's population basis (Dhaka division 46,744,804).
- Table-33 counts are deposit accounts, not people.
- BB spells Narsingdi "Narshingdi".

## Licence
None stated → `null`.
