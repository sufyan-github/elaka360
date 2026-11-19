# Fuel stations and LPG dealers of state oil companies (FUEL_STATIONS_<CODE>_2026)

`fetch.py` lives in `fuel_stations_raj_2026/` and writes `fuel_stations_<code>_2026/`. Key `FUEL_STATIONS_<CODE>_2026`, kind `fuel_stations`, source type `government_portal`, trust 4.

**Sources.**

| Source | Used? | Why |
|---|---|---|
| Padma Oil (pocl.gov.bd) "ডিলার (ফিলিং স্টেশান)" PDF: 918 stations, English, one heading per district | yes | Text PDF, read with `pdftotext` |
| Padma Oil "এল পি জি ডিলার" PDF: 884 dealers | yes | Same format |
| Meghna Petroleum (mpl.gov.bd "কাস্টমার তথ্য") filling-station and LPG lists | no | Scanned PDFs with no text |
| Jamuna Oil filling-station list | no | On Google Drive; drive.google.com robots.txt disallows the download path `/uc` |
| Jamuna Oil LPG-dealer PDF | no | Old Bijoy-encoded text with owners' names and mobiles |
| RPGCL (rpgcl.org.bd) CNG | no | Monthly counts only (Oct 2026: 606 approved, 504 operating stations), no list |
| BPC depot page | no | Empty |
| Portal petrol-pump lists | no | Dinajpur Sadar is a scan; Sitakunda has garbled text plus managers' mobiles. Both noted in `facts.csv` |

**Normalisation.**
- `name_en` and `address` are as printed (upper case), split at the page's address column. Lines that wrap are appended to the address, with a note.
- `district_en` is the printed district heading normalised to the seed (BOGRA→Bogura, NAWABGONJ→Chapainawabganj, JESSORE→Jashore, JHALAKHATI→Jhalokathi). The printed heading is kept in `extra_json`.
- `upazila_en` is set only when exactly one seed upazila name of that district appears in the address (noted "inferred").
- Addresses that name the proprietor ("PROP./MR./MD. …") are left empty.
- There are no phone numbers or coordinates.
- LPG dealers have no fitting category: they use top-level `business` with proposed subcategory `business.lpg_dealer`.
- `extra_json` holds the dealer account number, PDF page and list page. `source_url` is the PDF.

**Counts.**

| Division | Filling stations | LPG dealers | Total | With upazila |
|---|---|---|---|---|
| Rajshahi | 113 | 152 | 265 | 89 |
| Rangpur | 156 | 88 | 244 | 68 |
| Dhaka | 269 | 61 | 330 | 60 |
| Chattogram | 147 | 375 | 522 | 143 |
| Khulna | 118 | 153 | 271 | 60 |
| Barishal | 10 | 25 | 35 | 9 |
| Sylhet | 68 | 30 | 98 | 7 |
| Mymensingh | 37 | 0 | 37 | 10 |

**Doubts.**
- The lists are undated. Padma Oil's pages say they were last updated in 2019 and the files were re-uploaded in December 2024, so closed stations probably remain.
- A few dealers sit under the wrong district heading in the PDF (e.g. "BIROL BAZAR" under DHAKA); kept as printed.
- A few names spill into the address column.
- Many LPG "dealers" are listed under the owner's own name; that is the name Padma Oil publishes.

Licence: none stated; state-company public information, cite Padma Oil PLC.
