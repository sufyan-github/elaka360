# BD_RAILWAY_BAR_2026 — Bangladesh Railway (Barishal Division)

**Source:** railway.gov.bd (trust level 4), accessed 2026-11-18, via `bd_railway_raj_2026/fetch.py --division barishal`. Two pages were checked:
- "গুরুত্বপূর্ন স্টেশনের টেলিফোন" (kept as `raw/railway_important_station_phones.txt`);
- Information Book 2023-2024, Table-4 (district-wise stations and route km; national table, kept as `raw/infobook_2023_24_table4.txt`).

## Result: nothing for this division

- **Barishal Division has no railway.** Table-4 lists 49 districts with 542 stations and 3355.777 route km. None of them is Barishal, Bhola, Patuakhali, Pirojpur, Jhalokathi or Barguna.
- **The phone list** names no station in the division.
- **`places.csv` and `facts.csv`** are header-only. No zero values are written, because the source gives none.
- **Collector change:** `fetch.py` now accepts `--division barishal`. A division without Table-4 districts writes no division-sum facts.

## Gaps
- There is no public station register, and eticket.railway.gov.bd is disallowed by robots.txt.
- **Licence:** none stated.
