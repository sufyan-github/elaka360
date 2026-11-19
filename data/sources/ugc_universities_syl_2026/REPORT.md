# UGC university register — Sylhet Division

- **Source:** all universities on www.ugc.gov.bd/universities (public, private, international and CBHE lists, plus each `/university/<slug>` page; robots.txt allows). Collected with `ugc_universities_raj_2026/fetch.py --division sylhet`, accessed 2026-11-18. No page failed.
- **Selection:** a university is kept if its UGC campus address names a Sylhet-Division district. When an address names several districts, the one named last decides; the districts of all other divisions are also checked. A trailing "Sylhet" after another Sylhet-Division district is read as the division. UGC's spelling "Hobiganj" is recognised. When UGC gives no address, the university is kept (flagged) if its name names a district; none did for Sylhet.
- **Licence:** none stated.

## Result: 10 universities (5 public, 5 private)

| District | Universities |
|---|---|
| Sylhet (8) | Shahjalal University of Science & Technology, Sylhet Agricultural University, Sylhet Medical University (public); Leading University, Metropolitan University, North East University Bangladesh, Sylhet International University, R.T.M Al-Kabir Technical University (private) |
| Habiganj | Hobiganj Agricultural University (public) |
| Sunamganj | Sunamganj Science and Technology University (public) |
| Moulvibazar | none |

## Fields

- **Contacts:**
  - Phones on 6 rows: landlines and hotlines only, mobile numbers dropped. R.T.M Al-Kabir, Sylhet Medical University, Hobiganj Agricultural University and Sunamganj S&T University list only mobile numbers, so their phone stays empty.
  - E-mails and websites on all 10 rows. Officials' names are dropped.
  - SUST: one personal-looking free-mail address is dropped (registrar@sust.edu is kept).
  - North East University: "registrar@neub@edu,bd" is malformed and dropped (info@neub.edu.bd is kept).
- **Free-mail address kept as institutional-looking:** Sylhet Medical University (bsfmmusylhet@gmail.com). Its UGC website is www.bsfmmu.edu.bd, as published.
- **Hobiganj Agricultural University:** its e-mails vc@hau.ac.bd and registraroffice@hau.ac.bd are office addresses on the university's own domain.
- **Upazila:** set on 3 rows. Leading University ("South Surma") and Sylhet Medical University ("Dakshinsurma") → Dakshin Surma; Hobiganj Agricultural University → Habiganj Sadar. Sylhet-city addresses are not given a thana. No coordinates.
- **`extra_json`:** UGC category, year, campuses, postcode, fax, UGC id.

## Gaps and doubts

- **Bangla names:** UGC's page data has no Bangla name for these ten, so `name_bn` is empty.
- **`raw/`:** the raw JSON keeps UGC's contact fields as published (including the dropped mobile numbers and addresses), as for the earlier divisions.
- **Not included:** universities UGC lists without any address whose names name no district (the same national set as in the earlier reports).
