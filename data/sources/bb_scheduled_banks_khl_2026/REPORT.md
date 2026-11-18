# BB_SCHEDULED_BANKS_KHL_2026 — Bangladesh Bank, Scheduled Banks Statistics (Apr–Jun 2026), Khulna Division

**Source:** bb.org.bd quarterly Scheduled Banks Statistics, April–June 2026 (as on 30-06-2026), 8.5 MB PDF. It is not committed; `fetch.py --division khulna` re-downloads it and parses it with pdftotext. Trust level 4. Accessed 2026-11-18.

## Branch list: not available
There is no public branch list (names, addresses, routing numbers), and district branch counts are not published.

## Collected (facts only, 200 rows)
- **Branches (Table-3.16):** scheduled bank branches in the division at end-June 2026 — urban 547, rural 555, **total 1,102**. Transcribed from the table image, PDF page 35 / printed p. 27, "Khulna division" column.
- **Deposits and advances (Table-1):** division and all 10 districts, in BDT lakh, with per-capita values.

  | Area | Deposits (BDT lakh) | Advances (BDT lakh) |
  |---|---:|---:|
  | Khulna District | 2,979,245 | 2,269,308 |
  | Khulna Division | 9,995,969 | 6,722,789 |
- **Deposit accounts (Table-33):** division (18,304,666 accounts), 10 districts and 71 thanas, plus thana deposit amounts.
  - Thana names are as spelled by BB, mapped per district: Abhoynagar, Bagerpara, Chowgacha, Jhikargacha, Monirampur, Sarsha, Jhenidah Sadar, Harinakundu, Moheshpur, Sailkupa, Jiban Nagar, Paikgacha, Lohagora, Muzibnagar, Ashasuni.
  - Sadar-equivalents: Kotwali (Jashore) → Jashore Sadar, Meherpur → Meherpur Sadar, Narail → Narail Sadar.
  - `upazila_en` is set on 59 thanas (all 59 upazilas of the division). It is empty for:
    - the KMP thanas: Kotwali_Khulna, Daulatpur (Khulna), Harintana, Khalishpur, Khan Jahan Ali, Labonchora, Sonadanga;
    - Darshana, Benapole, Islami University, Naragati, Patkelghata (police stations, not upazilas).

## Data quality
- Table-1 per-capita values use BB's population basis (Khulna division 18,242,589).
- Table-33 counts are deposit accounts, not people.
- "Daulatpur" occurs twice: the KMP thana in Khulna district (not mapped) and the Kushtia upazila (mapped).

## Licence
None stated → `null`.
