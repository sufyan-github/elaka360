# DPE IPEMIS public school directory — Rangpur Division

- **Source:** ipemis.dpe.gov.bd/search-school (linked from dpe.gov.bd). No login. There is no robots.txt (404). Licence: none stated.
- **Method:** the Rajshahi collector, run as `python3 ../dpe_ipemis_primary_raj_2026/fetch.py --division rangpur` with IPEMIS `divisionId=7` (accessed 2026-11-17). It reads the listing endpoint (`/load-lite-school-list`) per district, 500 rows at a time. It also reads `api.ipemis.dpe.gov.bd/api/school-stat-public` for division, district and upazila statistics. `raw/` holds the division JSON (7.4 MB).
- **Scope:** government, newly nationalised and experimental primary schools only. Kindergartens, NGO schools and ebtedayee madrasas are not included.

## Counts: 9,546 schools

All rows are `education.primary_school` with ownership "government".

By type: 4,479 government, 5,059 newly nationalised, 8 experimental.

By district: Dinajpur 1,871 · Gaibandha 1,467 · Rangpur 1,456 · Kurigram 1,241 · Nilphamari 1,085 · Thakurgaon 999 · Lalmonirhat 763 · Panchagarh 664.

Rangpur District by upazila: Mithapukur 275, Pirganj 236, Rangpur Sadar 223, Gangachara 178, Pirgachha 178, Badarganj 176, Kaunia 115, Taraganj 75. IPEMIS has no separate city unit; city schools are under Rangpur Sadar.

The official live statistics match the listed rows for the division, every district and every upazila. The division total is 9,546 schools, 50,993 teachers and 1,301,142 students. Rangpur District has 1,456 schools, 8,064 teachers and 202,027 students.

`facts.csv` has 473 rows: the official statistics (schools, teachers and students per division, district and upazila) and counts of listed records by type.

## Fields and gaps

- **Names and address:** Bangla and English names (the English is often abbreviated). The address is union or ward, upazila and district, in Bangla.
- **`extra_json`:** school code, IPEMIS id, type, union, cluster, and teacher and student counts.
- **Not included:** there are no coordinates, phones or e-mails. Head teachers' names and mobiles on the detail pages are deliberately not collected.
- **Upazila names:** these are normalised to standard spellings and the original is kept in `upazila_src`. Examples: BIROL becomes Biral, KHANSHAMA becomes Khansama, SHUNDORGONJ becomes Sundarganj, and ROWMARI becomes Raumari. Kurigram's FULBARI becomes Phulbari.
- **Thakurgaon thanas:** IPEMIS lists **RUHIA** (77 schools) and **VULLI/Bhulli** (96 schools) in Thakurgaon as their own upazila units. These are thanas, not upazilas, so they are kept as `upazila_en` "Ruhia" and "Bhulli" with `admin_unit: thana` and a note. The source does not give their parent upazila. They are probably carved out of Thakurgaon Sadar, but this is not verified.
- **Repeated names:** 17 Bangla names repeat within an upazila under different codes.
- **Live data:** re-runs will differ.
