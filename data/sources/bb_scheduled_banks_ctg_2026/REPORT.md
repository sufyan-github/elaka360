# BB_SCHEDULED_BANKS_CTG_2026 — Bangladesh Bank, Scheduled Banks Statistics (Apr–Jun 2026), Chattogram Division

**Source:** bb.org.bd quarterly Scheduled Banks Statistics, April–June 2026 (as on 30-06-2026), 8.5 MB PDF. It is not committed; `fetch.py --division chattogram` re-downloads it and parses it with pdftotext. Trust level 4. Accessed 2026-11-17.

## Branch list: not available
There is no public branch list (names, addresses, routing numbers), and district branch counts are not published.

## Collected (facts only, 313 rows)
- **Branches (Table-3.16):** scheduled bank branches in the division at end-June 2026 — urban 1,435, rural 1,247, **total 2,682**. Transcribed from the table image, PDF page 35 / printed p. 27, "Chattogram division" column.
- **Deposits and advances (Table-1):** division and all 11 districts, in BDT lakh, with per-capita values.

  | Area | Deposits (BDT lakh) | Advances (BDT lakh) |
  |---|---:|---:|
  | Chattogram District | 27,946,808 | 30,424,621 |
  | Chattogram Division | 45,876,574 | 34,627,754 |
- **Deposit accounts (Table-33):** division (36,444,783 accounts), 11 districts and 125 thanas, plus thana deposit amounts.
  - Thana names are as spelled by BB, mapped per district: Naikhangchari, Rowangchari, Nasir Nagar, Matlab South → Matlab Dakshin, Fatikchari, Mirsarai, Maheskhali, Laksham → Laksam, Monohorganj → Manoharganj, Nangolkot, Lakshmichari, Mahalchari, Manikchari, Panchari, Hatia → Hatiya, Baghaichari, Belaichari, Juraichari, Kaowkhali → Kawkhali, Nanuerchar → Naniarchar.
  - Sadar-equivalents: Kotwali_Cumilla → Cumilla Adarsha Sadar, Cumilla Sadar South → Cumilla Sadar Dakshin, Kotwali_Rangamati → Rangamati Sadar, Sudharam → Noakhali Sadar, Khagrachari Sadar → Khagrachhari Sadar.
  - `upazila_en` is set on 104 thanas, including Karnaphuli. It is empty for:
    - the 15 CMP thanas: Akbor Shah, Baiozid Bostami, Bakolia, Bandar Ctg., Chandgaon, Chawkbazar, Double Mooring, Epz, Halishar, Kotwali_Chattogram, Kulshi, Pahartali, Panchlaish, Patenga, Sadarghat;
    - Bhujpur, Jorarganj, Bangora, Chandraganj, Chandraghona;
    - Char Jabber: kept as published and not mapped, because the table also lists Subarnachar.

## Data quality
- Table-1 per-capita values use BB's population basis (Chattogram division 35,002,453).
- Table-33 counts are deposit accounts, not people.
- BB spells "Cox'S Bazar" and "Khagrachari".

## Licence
None stated → `null`.
