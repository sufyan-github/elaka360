# BB_SCHEDULED_BANKS_MYM_2026 — Bangladesh Bank, Scheduled Banks Statistics (Apr–Jun 2026), Mymensingh Division

**Source:** bb.org.bd quarterly Scheduled Banks Statistics, April–June 2026 (as on 30-06-2026), 8.5 MB PDF. It is not committed; `fetch.py --division mymensingh` re-downloads it and parses it with pdftotext. Trust level 4. Accessed 2026-11-18.

## Branch list: not available
There is no public branch list (names, addresses, routing numbers), and district branch counts are not published.

## Collected (facts only, 100 rows)
- **Branches (Table-3.16):** scheduled bank branches in the division at end-June 2026 — urban 242, rural 231, **total 473**. Transcribed from the table image: PDF page 36, printed p. 28 (Table-3.16 Concld.), "Mymensingh division" column.
- **Deposits and advances (Table-1, Concl'd):** division and all 4 districts, in BDT lakh, with per-capita values.

  | Area | Deposits (BDT lakh) | Advances (BDT lakh) |
  |---|---:|---:|
  | Mymensingh District | 2,097,190 | 1,101,650 |
  | Jamalpur District | 796,968 | 481,897 |
  | Netrokona District | 434,038 | 310,050 |
  | Sherpur District | 294,921 | 305,999 |
  | Mymensingh Division | 3,623,117 | 2,199,596 |
- **Deposit accounts (Table-33):** division (7,849,394 accounts), 4 districts and 36 thanas, plus thana deposit amounts. The thana accounts add up to each district total.
  - Thana names are as spelled by BB, mapped per district: Bakshiganj → Bokshiganj, Dewanganj → Dewangonj, Goffargaon → Gafargaon, Ishwarganj → Iswarganj, Trisal → Trishal, Kaliajuri → Khaliajuri, Mohonganj → Mohongonj, Netrokona → Netrokona Sadar, Nakla → Nokla.
  - "Kotwali_Mymensingh" → Mymensingh Sadar (there is no metropolitan police; like "Kotwali_Bogura").
  - `upazila_en` is set on 35 thanas. It is empty for Pagla, a thana in Gafargaon upazila.

## Data quality
- **Population basis:** Table-1 per-capita values use BB's population basis (Mymensingh division 12,942,086).
- **Deposit totals differ between tables:** Table-1 gives 3,623,117 lakh for the division, Table-33 3,776,298. Table-1 excludes interbank deposits and accrued interest; division and district deposits are taken from Table-1.
- **Accounts:** Table-33 counts are deposit accounts, not people.

## Licence
None stated → `null`.
