# UGC university register — Mymensingh Division

- **Source:** all universities on www.ugc.gov.bd/universities (public, private, international and CBHE lists, plus each `/university/<slug>` page; robots.txt allows). Collected with `ugc_universities_raj_2026/fetch.py --division mymensingh`, accessed 2026-11-18. No page failed.
- **Selection:** a university is kept if its UGC campus address names a Mymensingh-Division district. When an address names several districts, the one named last decides; the districts of all other divisions are also checked. A trailing "Mymensingh" after another Mymensingh-Division district is read as the division. When UGC gives no address, the university is kept (flagged) if its name names a district; none did for Mymensingh.
- **Licence:** none stated.

## Result: 5 universities (4 public, 1 private)

| District | Universities |
|---|---|
| Mymensingh (2) | Bangladesh Agricultural University (1961), Jatiya Kabi Kazi Nazrul Islam University (Trishal, 2006) (public) |
| Jamalpur (2) | Jamalpur Science and Technology University (2018) (public); Brahmaputra International University (2013) (private) |
| Netrokona (1) | Netrokona University (2018) (public) |
| Sherpur | none |

## Fields

- **Phones:** on all 5 rows; landlines only, mobile numbers dropped (BAU, Netrokona University, Brahmaputra International University each listed one).
  - JKKNIU prints "09032-56212, 56214, 56217, …": only the first full number is kept. The bare 5-digit numbers after it are dropped by the collector's existing rule.
  - Jamalpur S&T University: "+8802-481100554-9" kept as printed (a number range).
- **E-mails:** on 4 rows; Jamalpur S&T University gives none. Officials' names are dropped.
  - Brahmaputra International University: vc@sfmu.edu.bd is dropped (its domain differs from the website sfmu.ac.bd); gmoula28@gmail.com is dropped as personal-looking; sfmuniversitybd@gmail.com is kept as institutional-looking.
- **Websites as published:** they carry earlier names: Netrokona University → www.shu.edu.bd, Jamalpur S&T University → bsfmstu.ac.bd, Brahmaputra International University → www.sfmu.ac.bd.
- **Upazila:** set on 1 row (JKKNIU → Trishal). Mymensingh-city and district-town addresses get no upazila. No coordinates.
- **`extra_json`:** UGC category, year, campuses, postcode, fax, UGC id.

## Gaps and doubts

- **Bangla names:** UGC's page data has no Bangla name for these five, so `name_bn` is empty.
- **`raw/`:** the raw JSON keeps UGC's contact fields as published (including the dropped mobile numbers and the personal-looking address), as for the earlier divisions.
- **Not included:** universities UGC lists without any address whose names name no district (the same national set as in the earlier reports).
