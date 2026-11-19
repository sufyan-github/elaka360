# Haat-bazaar lists on DC and upazila portals (HAAT_BAZAAR_<CODE>_2026)

`fetch.py` lives in `haat_bazaar_raj_2026/` and writes `haat_bazaar_<code>_2026/`. Key `HAAT_BAZAAR_<CODE>_2026`, kind `haat_bazaar`, source type `government_portal`, trust 4.

**Sources.** I read 559 DC and UNO portal home menus. From them I followed links titled হাটবাজার / হাট-বাজার / হাট বাজার / হাট বাজারের তালিকা; titles about price monitoring, committees and the like were excluded. That covers 523 portals. I also always tried `/pages/hatbazar`, the portal framework's built-in market list (paginated with `?page=N`).
- Page tables are read by their column headers, with merged cells expanded.
- Comma lists, numbered lists and "ঐ" ditto marks are handled.
- Lists published only as files (PDF, DOC, images) are counted in `facts.csv` but not parsed.
- The Department of Agricultural Marketing (dam.gov.bd) publishes no market list, only office lists and price bulletins.

**What is kept and what is never kept.**
- Kept, as published: market name, union (`union_bn`), the upazila as printed, address, haat days, area, number of chandina-bhiti stalls, and the managing authority.
- Dropped before anything is stored: any column or cell about the lease (ইজারা — this covers lease values, lessees' names and addresses, and any "authority" cell that names a lessee), informants, mobile numbers, remarks, and lease notes in brackets.
- Caption rows ("…উপজেলার হাট-বাজারের তথ্য") are dropped.
- Where a detail-page address contains a mobile number in its slug, `source_url` uses the list page instead.

**Normalisation.**
- `district_en` and `upazila_en` use the seed's names, matched on the Bangla name (e.g. Mohonpur, Bogra Sadar, Charrajibpur).
- On DC portals the upazila comes from the row's own text. City and pourashava markets on DC portals are left without an upazila, with a note.
- Category is `agriculture.haat` when the name contains "হাট" or market days are given, otherwise `business.market`.
- There are no coordinates and no phone numbers.
- A market listed on both the DC portal and an upazila portal keeps both rows; each row notes "also listed on …".

**Counts.**

| Division | Markets | haat / market | No upazila | From DC portal | Union given | Portals with ≥1 market / portals with a list | Portals with file-only lists |
|---|---|---|---|---|---|---|---|
| Rajshahi | 1,392 | 904 / 488 | 119 | 558 | 172 | 62/75 | 1 |
| Rangpur | 981 | 828 / 153 | 14 | 176 | 83 | 50/66 | 14 |
| Dhaka | 1,362 | 690 / 672 | 43 | 259 | 75 | 89/102 | 23 |
| Chattogram | 1,152 | 275 / 877 | 58 | 102 | 139 | 87/115 | 11 |
| Khulna | 1,131 | 860 / 271 | 78 | 178 | 98 | 55/69 | 4 |
| Barishal | 690 | 518 / 172 | 24 | 154 | 55 | 37/48 | 5 |
| Sylhet | 483 | 7 / 476 | 37 | 134 | 0 | 34/45 | 0 |
| Mymensingh | 493 | 56 / 437 | 25 | 71 | 112 | 34/39 | 9 |

Market days are published only in Khulna Division (39 rows).

**Doubts.**
- Some lists are old: lease calendars from 1417–1430 Bangla years, pages last edited 2012–2018.
- Some names carry suffixes ("-01", "(1)", "(পশু বাজারসহ)") or typos, kept as printed.
- Lists of names given without "হাট" or "বাজার" become `business.market`.
- Pages without a table, or with prose only, are skipped and noted in `facts.csv` (e.g. Akkelpur's lease-only table, Kalai's prose).
- Sylhet portals need extra CA intermediates; these are now added per division in `--division all` mode.

Licence: none stated; government public information, cite the portal.
