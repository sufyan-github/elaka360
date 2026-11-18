# UGC university register — Barishal Division

- **Source:** all universities on www.ugc.gov.bd/universities (public, private, international and CBHE lists, plus each `/university/<slug>` page; robots.txt allows). Collected with `ugc_universities_raj_2026/fetch.py --division barishal`, accessed 2026-11-18. No page failed.
- **Selection:** a university is kept if its UGC campus address names a Barishal-Division district. When an address names several districts, the one named last decides; the districts of all other divisions are also checked. A trailing "Barishal" after another Barishal-Division district is read as the division. UGC's spelling "Barisal" is recognised. When UGC gives no address, the university is kept (flagged) if its name names a district.
- **Licence:** none stated.

## Result: 6 universities (3 public, 3 private)

| District | Universities |
|---|---|
| Barishal (4) | University of Barishal (public, Barishal Sadar); Global University Bangladesh, University of Global Village, Trust University Barishal (private) |
| Patuakhali | Patuakhali Science and Technology University (public) |
| Pirojpur | Pirojpur Science & Technology University* (public) |
| Bhola, Jhalokathi, Barguna | none |

\* District taken from the name (UGC gives no address).

## Fields

- **Contacts:**
  - Phones on all 6 rows: landlines and hotlines only; mobile numbers are dropped.
  - E-mails on all 6 rows; websites on all 6. Officials' names are dropped.
  - Global University Bangladesh: two personal-looking free-mail addresses are dropped (only info@globaluniversity.edu.bd is kept).
- **Free-mail address kept as institutional-looking:** University of Global Village (ugvbarisal@gmail.com).
- **Upazila:** set on 1 row (University of Barishal, Barishal Sadar, from "Karnakathi, Barishal Sadar"). Barishal-city addresses are not given a thana. No coordinates.
- **`extra_json`:** UGC category, year, campuses, postcode, fax, UGC id.

## Gaps and doubts

- **Bangla names:** UGC's page data has no Bangla name for these six, so `name_bn` is empty.
- **Patuakhali Science and Technology University:** UGC's address names only "Patuakhali-8602", so `upazila_en` stays empty.
- **`raw/`:** the raw JSON keeps UGC's contact fields as published (including the dropped mobile numbers and free-mail addresses), as for the earlier divisions.
- **Not included:** universities UGC lists without any address whose names name no district (the same national set as in the earlier reports).
