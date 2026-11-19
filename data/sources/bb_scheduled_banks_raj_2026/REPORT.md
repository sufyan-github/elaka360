# BB_SCHEDULED_BANKS_RAJ_2026 — Bangladesh Bank, Scheduled Banks Statistics (Apr–Jun 2026)

**Source:** bb.org.bd → Publications → Quarterly → Scheduled Banks Statistics, latest issue April–June 2026 (as on 30-06-2026),
341-page PDF (8.5 MB, not committed; `fetch.py` re-downloads and parses it with poppler `pdftotext`). Trust level 4. Accessed 2026-11-12.

## Branch list: not available
Bangladesh Bank publishes **no public, filterable scheduled-bank branch list** (no branch names, addresses or routing numbers).
The routing-number URL and `robots.txt` return the site's WAF "Request Rejected" page. District-level **branch counts are not published**
either — only division level (Table-3.16, an image).

## Collected (facts only, 204 rows)
- Division: scheduled bank branches end-June 2026 — urban 600, rural 542, **total 1,142** (Table-3.16, transcribed from the image).
- Division + 8 districts (Table-1): deposits, advances (BDT lakh) and per-capita deposits/advances. E.g. Rajshahi District deposits
  2,083,343 lakh, advances 2,113,283 lakh.
- Division, 8 districts and 78 thanas (Table-33): number of deposit accounts; thana deposit amounts (BDT lakh). Rajshahi District
  thanas include RMP thanas (Boalia, Rajpara, Motihar, Shah Makdum, Airport, Katakhali, Kornohar) as spelled by BB; Chandrima,
  Belpukur, Damkura and Kashiadanga do not appear separately. Non-upazila thanas have empty `upazila_en`.

## Data quality
- Table-1 per-capita values use BB's own population basis (e.g. Rajshahi District 3,049,941), which may differ from the census.
- Table-33 account totals (e.g. division 17,382,793) are deposit accounts, not people.

## Licence
None stated → `null`.
