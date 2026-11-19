# UGC university register — Rangpur Division

- **Source:** all universities on www.ugc.gov.bd/universities (page data and each `/university/<slug>`; robots.txt allows), collected with `ugc_universities_raj_2026/fetch.py --division rangpur`, accessed 2026-11-17.
- **Selection:** a university is kept if its UGC campus address names a Rangpur-Division district. When an address also names another division's district, the district named last decides. When UGC gives no address, it is kept (flagged) if its name names one.
- **Licence:** none stated.

## Result: 7 universities (5 public, 2 private)

| District | Universities |
|---|---|
| Rangpur (2) | Begum Rokeya University (public); Teesta University\* (private) |
| Dinajpur | Hajee Mohammad Danesh Science & Technology University |
| Kurigram | Kurigram Agricultural University\* |
| Lalmonirhat | Aviation And Aerospace University, Bangladesh (UGC address "Lalmonirhat (in Process)") |
| Nilphamari (Saidpur) | Bangladesh Army University of Science and Technology (private) |
| Thakurgaon | Thakurgaon University |
| Panchagarh, Gaibandha | none |

\* District taken from the name (UGC gives no address).

Excluded: Pundra University of Science & Technology. Its address, "Rangpur Road, Gokul, Bogura-5800", is in Bogura, Rajshahi Division, and it is already in UGC_UNIVERSITIES_RAJ_2026.

## Fields

- **Contacts:** phones on 2 rows (landlines and hotlines only), institutional e-mails on 6, websites on 6. Officials' names are dropped.
- **`extra_json`:** UGC category, year, campuses, postcode, UGC id.
- **Location:** upazila only for BAUST (Saidpur); no coordinates.
- **Thakurgaon University** has no website, phone or e-mail on UGC.
- **Teesta University's** only e-mail is a gmail address belonging to the university; it is kept as institutional-looking.
