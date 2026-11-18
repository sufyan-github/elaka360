# UGC university register — Khulna Division

- **Source:** all 181 universities on www.ugc.gov.bd/universities (61 public, 116 private, 3 international, 1 CBHE; page data and each `/university/<slug>`; robots.txt allows), collected with `ugc_universities_raj_2026/fetch.py --division khulna`, accessed 2026-11-18.
- **Selection:** a university is kept if its UGC campus address names a Khulna-Division district. When an address names several districts, the one named last decides; the districts of all other divisions are also checked. A trailing "Khulna" after another Khulna-Division district is read as the division. UGC's spelling "Jessore" is recognised. When UGC gives no address, the university is kept (flagged) if its name names a district.
- **Licence:** none stated.

## Result: 14 universities (7 public, 7 private)

| District | Universities |
|---|---|
| Khulna (8) | 4 public: Khulna University, KUET, Khulna Agricultural University*, Khulna Medical University*. 4 private: North Western University, Northern University of Business & Technology Khulna, Khulna Khan Bahadur Ahsanullah University, Bangladesh Army University of Science and Technology Khulna (Phultala). |
| Kushtia (3) | Islamic University, Bangladesh (public); Rabindra Maitree University, Lalon University of Science and Arts (private) |
| Jashore | Jessore University of Science & Technology (public) |
| Chuadanga | First Capital University of Bangladesh (private) |
| Meherpur | Meherpur University* (public) |
| Satkhira, Bagerhat, Narail, Magura, Jhenaidah | none |

\* District taken from the name (UGC gives no address).

## Fields

- **Contacts:** phones on 8 rows (landlines and hotlines only; mobile numbers are dropped), e-mails on 11, websites on 12. Officials' names are dropped.
- **Free-mail addresses kept as institutional-looking:** BAUST Khulna (registrar.baustkhulna.edu.bd@gmail.com), KKBAU (registrar.kkbau@gmail.com, kkbau.edu.bd@gmail.com), Meherpur University (meherpuruniversity@gmail.com).
- **Upazila:** set on 1 row (BAUST Khulna, Phultala). Khulna-city metropolitan thanas (Sonadanga, Harintana, Khalishpur …) are not set. No coordinates.
- **`extra_json`:** UGC category, year, campuses, postcode, fax, UGC id.

## Gaps and doubts

- **Islamic University:** UGC's address is "Islamic University, Kushtia-7003"; the campus lies on the Kushtia–Jhenaidah border. Kept under Kushtia as UGC writes it.
- **Khulna Medical University** links to shmu.ac.bd (its former name); kept as UGC prints it.
- **Not included:** universities UGC lists without any address whose names name no district (the same national set as in the Dhaka report).
- **Present and permanent campus differ** (address = present campus): First Capital University of Bangladesh.
